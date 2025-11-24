from backtrack import CSP
from backtrack import branch_and_bound
from backtrack import define_inputs
from backtrack import best_solution
import random




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

variables, domains, constraints = define_inputs(cases, barristers, travel_times)
csp = CSP(variables, domains, constraints, costs)

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

print(f"\nRuntime: {end_time - start_time:.4f} seconds")
print(f"Peak memory: {peak / 10**6:.2f} MB")
#print(f"\nSolution: {result}")
#print(best_solution)

def evaluate():
    cases.sort(key=lambda x: x["time"])
    scores = {}
    locations = {}
    for barrister in barristers:
        name = barrister["name"]
        scores[name] = 0
        locations[name] = barrister["home"]

    for case in cases:
        barrister = best_solution[case]
        scores[barrister] += (case["duration"] + travel_times[(locations[barrister], case["location"])])
        locations[barrister] = case["location"]

    for barrister in barristers:
        name = barrister["name"]
        scores[name] += travel_times[(locations[name], barrister["home"])]



        
    return
