from backtrack import CSP
from backtrack import branch_and_bound
from backtrack import define_inputs
from backtrack import best_solution
from backtrack import best_sol
from ortoolssolver import setup_ortools_model
from ortoolssolver import solve_ortools_model
import random
import time, tracemalloc




locations = ["London", "Cambridge", "Oxford"]
barristers = [
    {"name": "Alice", "senority": 3, "schedule": []},
    {"name": "Bob", "senority": 2, "schedule": []},
    {"name": "Charlie", "senority": 4, "schedule": []},
]
cases = [
    {"name": "Case1", "time": 9, "duration": 3, "senority": 2, "location": "London"},
    {"name": "Case2", "time": 12, "duration": 2, "senority": 3, "location": "Cambridge"},
    {"name": "Case3", "time": 15, "duration": 1, "senority": 1, "location": "Oxford"},
]

travel_times = {
    ("London", "Cambridge"): 1,
    ("Cambridge", "London"): 1,
    ("London", "Oxford"): 2,
    ("Oxford", "London"): 2,
    ("Cambridge", "Oxford"): 1,
    ("Oxford", "Cambridge"): 1,
}

costs = {
    "Case1": {"Alice": 6, "Bob": 8, "Charlie": 5},
    "Case2": {"Alice": 7, "Bob": 5, "Charlie": 6},
    "Case3": {"Alice": 4, "Bob": 6, "Charlie": 8},
}

travel_times = {
    ("London", "Cambridge"): 1,
    ("Cambridge", "London"): 1,
    ("London", "Oxford"): 2,
    ("Oxford", "London"): 2,
    ("Cambridge", "Oxford"): 1,
    ("Oxford", "Cambridge"): 1,
    ("London", "London"): 0,
    ("Oxford", "Oxford"): 0,
    ("Cambridge", "Cambridge"): 0
}

cases = [
    {"name": "Case1", "time": 9, "duration": 2, "senority": 2, "location": "London"},
    {"name": "Case2", "time": 10, "duration": 3, "senority": 3, "location": "Cambridge"},
    {"name": "Case3", "time": 11, "duration": 2, "senority": 1, "location": "Oxford"},
    {"name": "Case4", "time": 13, "duration": 2, "senority": 2, "location": "London"},
    {"name": "Case5", "time": 14, "duration": 1, "senority": 1, "location": "Cambridge"},
    {"name": "Case6", "time": 15, "duration": 2, "senority": 3, "location": "Oxford"},
]

barristers = [
    {"name": "Alice", "senority": 4, "schedule": []},
    {"name": "Bob", "senority": 3, "schedule": [
        {"start_time": 8, "end_time": 9, "location": "London"}  # already busy early
    ]},
    {"name": "Charlie", "senority": 2, "schedule": [
        {"start_time": 11, "end_time": 12, "location": "Cambridge"}
    ]},
    {"name": "Dana", "senority": 3, "schedule": [
        {"start_time": 16, "end_time": 17, "location": "Oxford"}  # busy late
    ]},
]

costs = {
    "Case1": {"Alice": 6, "Bob": 7, "Charlie": 5, "Dana": 8},
    "Case2": {"Alice": 5, "Bob": 6, "Charlie": 8, "Dana": 7},
    "Case3": {"Alice": 7, "Bob": 8, "Charlie": 6, "Dana": 5},
    "Case4": {"Alice": 6, "Bob": 5, "Charlie": 7, "Dana": 8},
    "Case5": {"Alice": 5, "Bob": 7, "Charlie": 6, "Dana": 6},
    "Case6": {"Alice": 7, "Bob": 6, "Charlie": 9, "Dana": 5},
}

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
    {"name": f"Barr{i}", "senority": (i % 3) + 1, "home": f"Loc{(i%5)+1}", "schedule": []}
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
        "senority": (i % 3) + 1  # 1,2,3 cycling
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
        if barr["senority"] < case["senority"]:
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
"""
cases_sorted = sorted(cases, key=lambda c: c["time"])
variables, domains, constraints = define_inputs(cases_sorted, barristers, travel_times)
csp = CSP(variables, domains, constraints, case_costs)

import time, tracemalloc
tracemalloc.start()
start_time = time.time()

print("running")
#MRV_variables = sorted(csp.variables, key=lambda var: len(csp.domains[var]))
branch_and_bound({}, set(variables), 0, csp)
print("done")

end_time = time.time()
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
best_sol()

print(f"\nRuntime: {end_time - start_time:.4f} seconds")
print(f"Peak memory: {peak / 10**6:.2f} MB")
#print(f"\nSolution: {result}")
#print(best_solution)
"""
def calculate_costs(cases, barristers):
    case_costs = {}
    for case in cases:
        for barrister in barristers:
            cost = 600
            if case["type"] in barrister["expertise"]:
                cost -= 200
            cost -= min(200, barrister["experience"]*10)
            cost -= 200*barrister["winrate"]
            case_costs[(case["name"], barrister["name"])] = cost

    return case_costs





def evaluate():
    cases.sort(key=lambda x: x["time"])
    scores = {}
    locations = {}
    for barrister in barristers:
        name = barrister["name"]
        scores[name] = 0
        locations[name] = barrister["home"]

    for case in cases:
        if case in best_solution:
            barrister = best_solution[case] 
            scores[barrister] += (case["duration"] + travel_times[(locations[barrister], case["location"])])
            locations[barrister] = case["location"]

    for barrister in barristers:
        name = barrister["name"]
        scores[name] += travel_times[(locations[name], barrister["home"])]

    total_1= 0
    total_2 = 0
    total_sqr = 0
    n = 0
    for score1 in scores.values():
        n += 1
        total_1 += score1
        total_sqr += (score1**2)
        for score2 in scores.values():
            total_2 += abs(score1-score2)
    
    gini = total_1 / (2 * n * total_2)
    jain = total_1**2 / (n * total_sqr)

    return gini, jain


def solve_cases(cases, barristers, travel_times,
                assignment_fixed=None,
                method="ortools",
                **kwargs):

    """
    Solve the case assignment problem using the chosen method.
    
    method options:
        - "ortools"
        - "backtracking"
    """
    
    output = {}

    if method == "ortools":
        cases_sorted = sorted(cases, key=lambda c: c["time"])

        model, assign = setup_ortools_model(
            cases_sorted,
            case_costs,
            barristers,
            travel_times,
            assignment_fixed=None,
        )

        tracemalloc.start()
        start_time = time.time()

        result = solve_ortools_model(model, assign, cases_sorted, 30)

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        output["result"] = result
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6

    elif method == "backtracking":

        cases_sorted = sorted(cases, key=lambda c: c["time"])
        variables, domains, constraints = define_inputs(cases_sorted, barristers, travel_times)
        csp = CSP(variables, domains, constraints, case_costs)


        tracemalloc.start()
        start_time = time.time()

        branch_and_bound({}, set(variables), 0, csp)

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        output["result"] = best_sol()
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6


    else:
        raise ValueError(f"Unknown method: {method}")

    return result
