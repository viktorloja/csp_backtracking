from ortools.sat.python import cp_model

def setup_ortools_model(cases, case_costs, barristers, travel_times, assignment_fixed=None):
    n = len(cases)

    barrister_names = [b["name"] for b in barristers]

    model = cp_model.CpModel()

    # only assign barristers to cases they could take
    assign = {}
    for i, case in enumerate(cases):
        cstart = case["time"]
        cend = cstart + case["duration"]
        for b in barristers:
            # seniority filter
            if b["seniority"] < case.get("seniority", 0):
                continue
            # check schedule feasibility
            feasible = True
            for block in b.get("schedule", []):
                start, end = block["start_time"], block["end_time"]
                loc = block.get("location")
                travel = travel_times.get((loc, case["location"]))
                if not (cend + travel <= start or end + travel <= cstart): # if we cannot do case before or after this block then infeasible
                    feasible = False
                    break
            if feasible:
                assign[(i, b["name"])] = model.NewBoolVar(f"assign_c{i}_{case['name']}__b_{b['name']}")

    # each case only assigned 1 barrister
    for i in range(n):
        model.Add(sum(assign[(i,b)] for (ii,b) in assign if ii==i) == 1)

    # fix assignments as provided
    if assignment_fixed:
        for cname, bname in assignment_fixed.items():
            i = next(idx for idx,c in enumerate(cases) if c["name"]==cname)
            if (i, bname) in assign:
                model.Add(assign[(i,bname)] == 1)
            for key in list(assign):
                if key[0]==i and key[1]!=bname:
                    model.Add(assign[key] == 0)

    # travel constraints-
    for i in range(n-1):
        case1 = cases[i]
        start1, end1, loc1 = case1["time"], case1["time"]+case1["duration"], case1["location"]
        for j in range(i+1, n):
            case2 = cases[j]
            start2, end2, loc2 = case2["time"], case2["time"]+case2["duration"], case2["location"]

            # compute travel feasibility
            travel = travel_times.get((loc1, loc2), None)
            feasible = travel is not None and start2 >= end1 + travel

            # if overlap or infeasible travel, forbid same barrister
            if not feasible:
                for b in barrister_names:
                    if (i,b) in assign and (j,b) in assign:
                        model.Add(assign[(i,b)] + assign[(j,b)] <= 1)

    # next variables for travel minimization
    next_var = {}
    for b in barrister_names:
        for i in range(n):
            for j in range(i+1, n):
                if (i,b) in assign and (j,b) in assign:
                    if cases[j]["time"] >= cases[i]["time"] + cases[i]["duration"]:
                        next_var[(b,i,j)] = model.NewBoolVar(f"next__b_{b}__c{i}_to_c{j}")
                        model.Add(next_var[(b,i,j)] <= assign[(i,b)])
                        model.Add(next_var[(b,i,j)] <= assign[(j,b)])
                        for k in range(i+1,j):
                            if (k,b) in assign:
                                model.Add(next_var[(b,i,j)] + assign[(k,b)] <= 1)
                        model.Add(next_var[(b,i,j)] >= assign[(i,b)] + assign[(j,b)] - 1 - sum(assign[(k,b)] for k in range(i+1,j) if (k,b) in assign))

    # link next variables to assignments
    for b in barrister_names:
        for i in range(n):
            later = [j for j in range(i+1,n) if (b,i,j) in next_var]
            if not later:
                continue
            y = model.NewBoolVar(f"hasLater__b_{b}__c{i}")
            # force y to equal 1 if later case exists, 0 otherwise
            model.Add(sum(next_var[(b,i,j)] for j in later) >= y) 
            model.Add(sum(next_var[(b,i,j)] for j in later) <= len(later)*y) 
            # z = assign(i,b) AND y
            z = model.NewBoolVar(f"z_forward__b_{b}__c{i}")
            # force z to equal 1 if there is a case after i, 0 otherwise
            model.Add(z <= assign[(i,b)])
            model.Add(z <= y)
            model.Add(z >= assign[(i,b)] + y - 1)
            model.Add(sum(next_var[(b,i,j)] for j in later) == z)
            # ensure only one forward arc per case

    # minimize travel times and barrister costs (for taking cases)
    travel_terms = []
    for (b,i,j), var in next_var.items():
        loc_i = cases[i]["location"]
        loc_j = cases[j]["location"]
        travel = travel_times.get((loc_i, loc_j), 9999)
        travel_terms.append(travel*var)

    cost_terms = []
    for (i,b), var in assign.items():
        cname = cases[i]["name"]
        cost = case_costs.get((cname, b), 9999) 
        cost_terms.append(cost * var)

    model.Minimize(sum(travel_terms) + sum(cost_terms))


    return model, assign

def solve_ortools_model(model, assign, cases, max_time_seconds):
    # solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    status = solver.Solve(model)

    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        solution = {}
        for (i,b), var in assign.items():
            if solver.Value(var):
                solution[cases[i]["name"]] = b
        return {
            "status": solver.StatusName(status),
            "assignment": solution,
            "objective_score": solver.ObjectiveValue()
        }
    else:
        return {"status": solver.StatusName(status), "assignment": None}
    
"""
import hashlib

# ----------------------------
# Deterministic cost function
# ----------------------------
def deterministic_cost(case_name, barr_name):
    h = int(hashlib.sha256((case_name + barr_name).encode()).hexdigest(), 16)
    return (h % 10) + 1  # cost between 1–10

# ----------------------------
# Barristers
# ----------------------------
barristers = [
    {"name": f"Barr{i}", "seniority": (i % 3) + 1, "home": f"Loc{(i%5)+1}", "schedule": []}
    for i in range(8)
]

# ----------------------------
# Cases (50 cases, spaced 15–30 mins apart)
# ----------------------------
cases = []
for i in range(50):
    case = {
        "name": f"Case{i}",
        "time": 9*60 + i*15,  # start at 9:00am, every 15 mins
        "duration": 30 + (i % 3) * 5,  # 30–40 mins
        "location": f"Loc{(i % 5) + 1}",  # cycles through 5 locations
        "seniority": (i % 3) + 1  # 1,2,3 cycling
    }
    cases.append(case)

# ----------------------------
# Travel times between 5 locations (symmetric)
# ----------------------------
travel_times = {}
locations = [f"Loc{i}" for i in range(1,6)]
for loc1 in locations:
    for loc2 in locations:
        if loc1 == loc2:
            travel_times[(loc1, loc2)] = 0
        else:
            # deterministic "random" travel 10–60 mins
            travel_times[(loc1, loc2)] = 10 + (abs(ord(loc1[-1])-ord(loc2[-1]))*10)
            travel_times[(loc2, loc1)] = travel_times[(loc1, loc2)]

# ----------------------------
# Case costs
# ----------------------------
case_costs = {}
for case in cases:
    for barr in barristers:
        if barr["seniority"] < case["seniority"]:
            cost = 10**6  # prohibit infeasible seniority
        else:
            cost = deterministic_cost(case["name"], barr["name"])
        case_costs[(case["name"], barr["name"])] = cost

# ----------------------------
# Notes:
# - Feasibility guaranteed: multiple barristers can cover each case.
# - Travel distances and durations create overlaps, forcing OR-Tools to make scheduling decisions.
# - Deterministic costs ensure reproducible results.
# ----------------------------

cases = [
    {"name": "CaseB", "time": 10*60, "duration": 60, "location": "Court2", "seniority": 1},
]

case_costs = {
    ("CaseA", "Alice"): 10,
    ("CaseB", "Alice"): 10,
    ("CaseC", "Alice"): 10,
    ("CaseD", "Alice"): 10,

    ("CaseA", "Bob"): 8,
    ("CaseB", "Bob"): 8,
    ("CaseC", "Bob"): 8,
    ("CaseD", "Bob"): 8,
}

barristers = [
    {
        "name": "Alice",
        "seniority": 2,
        "schedule": [
            # Alice is busy right in the middle of CaseB window
            {"start_time": 14*60, "end_time": 14*60+30, "location": "Court2"}
        ]
    },
]

# Travel times between courts are deliberately large (impossible to chain cases)
travel_times = {
    ("Court1", "Court2"): 45,
    ("Court2", "Court2"): 0,
    ("Court3", "Court1"): 45,

    ("Court2", "Court1"): 45,
    ("Court3", "Court2"): 45,
    ("Court1", "Court3"): 45,

    ("Chambers", "Court1"): 30,
    ("Chambers", "Court2"): 30,
    ("Chambers", "Court3"): 30,

    ("Court1", "Chambers"): 30,
    ("Court2", "Chambers"): 30,
    ("Court3", "Chambers"): 30,
}


cases_sorted = sorted(cases, key=lambda c: c["time"])
model, assign = setup_ortools_model(
    cases_sorted,
    case_costs,
    barristers,
    travel_times,
    assignment_fixed=None,
)

res = solve_ortools_model(model, assign, cases_sorted, 30)
print("Status:", res["status"])
print("Number of assignments:", len(res.get("assignment", {})))
print("Objective travel+cost:", res.get("objective_score", None))
print(res["assignment"])


"""