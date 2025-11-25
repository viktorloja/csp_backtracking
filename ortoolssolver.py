from ortools.sat.python import cp_model

def setup_ortools_model(cases, case_costs, barristers, travel_times, assignment_fixed=None):
    # ----- Preprocess & indexing -----
    n = len(cases)

    barrister_names = [b["name"] for b in barristers]

    model = cp_model.CpModel()

    # ----- Feasible assign variables only -----
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
            for blk in b.get("schedule", []):
                blk_s, blk_e = blk["start_time"], blk["end_time"]
                loc_blk = blk.get("location")
                t_to = travel_times.get((loc_blk, case["location"]))
                t_from = travel_times.get((case["location"], loc_blk))
                if cend + t_from > blk_s or blk_e + t_to > cstart:
                    feasible = False
                    break
            if feasible:
                assign[(i, b["name"])] = model.NewBoolVar(f"assign_c{i}_{case['name']}__b_{b['name']}")

    # ----- Each case assigned exactly one feasible barrister -----
    for i in range(n):
        model.Add(sum(assign[(i,b)] for (ii,b) in assign if ii==i) == 1)

    # ----- Partial fixed assignments -----
    if assignment_fixed:
        for cname, bname in assignment_fixed.items():
            i = next(idx for idx,c in enumerate(cases) if c["name"]==cname)
            if (i, bname) in assign:
                model.Add(assign[(i,bname)] == 1)
            for key in list(assign):
                if key[0]==i and key[1]!=bname:
                    model.Add(assign[key] == 0)

    # ----- No-overlap / travel constraints -----
    for i in range(n):
        ci = cases[i]
        si, ei, loc_i = ci["time"], ci["time"]+ci["duration"], ci["location"]
        for j in range(i+1, n):
            cj = cases[j]
            sj, ej, loc_j = cj["time"], cj["time"]+cj["duration"], cj["location"]

            # compute travel feasibility
            travel_ij = travel_times.get((loc_i, loc_j), None)
            travel_ji = travel_times.get((loc_j, loc_i), None)
            feasible_ij = travel_ij is not None and sj >= ei + travel_ij
            feasible_ji = travel_ji is not None and si >= ej + travel_ji

            # if overlap or infeasible travel, forbid same barrister
            if not (feasible_ij or feasible_ji) or not (ej <= si or ei <= sj):
                for b in barrister_names:
                    if (i,b) in assign and (j,b) in assign:
                        model.Add(assign[(i,b)] + assign[(j,b)] <= 1)

    # ----- Successor (next) variables for travel minimization -----
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

    # ----- Link next variables to assignments (forward) -----
    for b in barrister_names:
        for i in range(n):
            later = [j for j in range(i+1,n) if (b,i,j) in next_var]
            if not later:
                continue
            y = model.NewBoolVar(f"hasLater__b_{b}__c{i}")
            #force y to equal 1 if later case exists, 0 otherwise
            model.Add(sum(next_var[(b,i,j)] for j in later) >= y) 
            model.Add(sum(next_var[(b,i,j)] for j in later) <= len(later)*y) 
            # z = assign(i,b) AND y
            z = model.NewBoolVar(f"z_forward__b_{b}__c{i}")
            #force z to equal 1 if there is a case after i, 0 otherwise
            model.Add(z <= assign[(i,b)])
            model.Add(z <= y)
            model.Add(z >= assign[(i,b)] + y - 1)
            model.Add(sum(next_var[(b,i,j)] for j in later) == z)
            #ensure only one forward arc per case

    # ----- Objective: minimize total travel along consecutive edges -----
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
    # ----- Solve -----
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
    
# ----------------------------
# Test Case With Case Costs
# ----------------------------

cases = [
    {"name": "A", "time": 9*60,      "duration": 60, "location": "Loc1", "seniority": 1},
    {"name": "B", "time": 10*60+30,  "duration": 60, "location": "Loc1", "seniority": 1},
    {"name": "C", "time": 14*60,     "duration": 60, "location": "Loc2", "seniority": 2},
    {"name": "D", "time": 15*60+30,  "duration": 60, "location": "Loc2", "seniority": 1},
]

barristers = [
    {"name": "Alice",   "seniority": 3, "home": "Loc1", "schedule": []},
    {"name": "Bob",     "seniority": 1, "home": "Loc1", "schedule": []},
    {"name": "Charlie", "seniority": 2, "home": "Loc2", "schedule": []},
]

# Travel times matrix
travel_times = {
    ("Loc1","Loc1"): 0,
    ("Loc2","Loc2"): 0,
    ("Loc1","Loc2"): 90,
    ("Loc2","Loc1"): 90,
}

# ----------------------------
# Cost dictionary for each (case,barrister)
# ----------------------------
# cost = penalty, price, preference, etc.

case_costs = {
    ("A", "Alice"):   3,
    ("A", "Bob"):     8,
    ("A", "Charlie"): 6,

    ("B", "Alice"):   2,
    ("B", "Bob"):     5,
    ("B", "Charlie"): 7,

    ("C", "Alice"):   9,
    ("C", "Bob"):     999,   # Bob can't take C (seniority too low), but cost included for completeness
    ("C", "Charlie"): 1,

    ("D", "Alice"):   4,
    ("D", "Bob"):     3,
    ("D", "Charlie"): 4,
}



import random
from datetime import timedelta

# --------------------------

# ----------------------------
# Barristers
# ----------------------------
barristers = [
    {"name": "Alice", "seniority": 2, "home": "Loc1", "schedule": []},
    {"name": "Bob", "seniority": 1, "home": "Loc2", "schedule": []},
    {"name": "Charlie", "seniority": 3, "home": "Loc1", "schedule": []},
]

# ----------------------------
# Cases (times in minutes since midnight)
# ----------------------------
cases = [
    {"name": "A", "time": 9*60,  "duration": 60, "location": "Loc1", "seniority": 1},
    {"name": "B", "time": 10*60+30, "duration": 60, "location": "Loc1", "seniority": 1},
    {"name": "C", "time": 12*60, "duration": 60, "location": "Loc2", "seniority": 1},
    {"name": "D", "time": 14*60, "duration": 60, "location": "Loc2", "seniority": 2},
    {"name": "E", "time": 16*60, "duration": 60, "location": "Loc1", "seniority": 1},
]

# ----------------------------
# Travel times (symmetric, in minutes)
# ----------------------------
travel_times = {
    ("Loc1", "Loc1"): 0,
    ("Loc2", "Loc2"): 0,
    ("Loc1", "Loc2"): 60,
    ("Loc2", "Loc1"): 60,
}

# ----------------------------
# Case costs (lower = preferred)
# ----------------------------
case_costs = {
    ("A", "Alice"): 2,
    ("A", "Bob"): 5,
    ("A", "Charlie"): 3,

    ("B", "Alice"): 1,
    ("B", "Bob"): 6,
    ("B", "Charlie"): 2,

    ("C", "Alice"): 5,
    ("C", "Bob"): 1,
    ("C", "Charlie"): 3,

    ("D", "Alice"): 2,
    ("D", "Bob"): 10,  # Bob too low seniority for D but included as high cost
    ("D", "Charlie"): 1,

    ("E", "Alice"): 3,
    ("E", "Bob"): 8,
    ("E", "Charlie"): 2,
}

# ----------------------------
# Feasible assignment plan for reference:
# Alice: A, B, E
# Bob: C
# Charlie: D
# Travel times allow this:
#   - Alice moves Loc1→Loc1 between A/B/E: 0 min travel
#   - Bob: C only at Loc2, no conflicts
#   - Charlie: D only at Loc2, feasible
# ----------------------------


# ----------------------------
# Run OR-Tools solver
# ----------------------------

# ----------------------------
# Barristers
# ----------------------------
barristers = [
    {"name": "Alice", "seniority": 3, "home": "Loc1", "schedule": []},
    {"name": "Bob", "seniority": 2, "home": "Loc2", "schedule": []},
    {"name": "Charlie", "seniority": 2, "home": "Loc3", "schedule": []},
    {"name": "Diana", "seniority": 1, "home": "Loc1", "schedule": []},
    {"name": "Edward", "seniority": 2, "home": "Loc2", "schedule": []},
]

# ----------------------------
# Cases (times in minutes since midnight)
# ----------------------------
cases = [
    {"name": f"Case{i}", 
     "time": 9*60 + i*30,  # every 30 minutes
     "duration": 45, 
     "location": f"Loc{(i%3)+1}",  # cycles through Loc1, Loc2, Loc3
     "seniority": (i%3)+1}  # cycles 1,2,3
    for i in range(20)
]

# ----------------------------
# Travel times (in minutes)
# ----------------------------
travel_times = {
    ("Loc1","Loc1"):0, ("Loc2","Loc2"):0, ("Loc3","Loc3"):0,
    ("Loc1","Loc2"):30, ("Loc2","Loc1"):30,
    ("Loc1","Loc3"):45, ("Loc3","Loc1"):45,
    ("Loc2","Loc3"):20, ("Loc3","Loc2"):20,
}

# ----------------------------
# Case costs (lower = preferred)
# ----------------------------
case_costs = {}
for case in cases:
    for barrister in barristers:
        # Barristers with insufficient seniority get high cost
        if barrister["seniority"] < case["seniority"]:
            cost = 10**6
        else:
            # Randomized cost between 1–10
            cost = ((hash(case["name"] + barrister["name"]) % 10) + 1)
        case_costs[(case["name"], barrister["name"])] = cost

# ----------------------------
# Feasibility guaranteed:
# - Cases are spaced every 30 minutes
# - Duration = 45 mins → small overlaps
# - Travel times <= 45 mins → still feasible for some barristers
# - Seniorities cycle → some options are blocked, creating complexity
# ----------------------------
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


