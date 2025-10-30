from backtrack import CSP
from backtrack import backtrack
from backtrack import define_inputs


import random

def generate_consistent_test(num_cases=1000, num_barristers=1000, num_locations=5):
    random.seed(42)

    # --- Define locations ---
    locations = [f"Court{i}" for i in range(1, num_locations + 1)]

    # --- Generate realistic travel times ---
    travel_times = {}
    for loc1 in locations:
        for loc2 in locations:
            if loc1 == loc2:
                travel_times[(loc1, loc2)] = 0.0
            else:
                travel_times[(loc1, loc2)] = round(random.uniform(0.3, 1.5), 1)

    # --- Generate barristers ---
    barristers = []
    for i in range(num_barristers):
        seniority = random.randint(1, 3)
        # Fewer schedule blocks -> more availability -> easier to solve
        num_blocks = random.randint(0, 1)
        schedule = []
        for _ in range(num_blocks):
            start = random.uniform(8.0, 12.0)
            end = start + random.uniform(1.0, 2.0)
            schedule.append({
                "start_time": round(start, 1),
                "end_time": round(end, 1),
                "location": random.choice(locations)
            })
        schedule.sort(key=lambda b: b["start_time"])

        barristers.append({
            "name": f"Barrister_{i+1}",
            "senority": seniority,
            "schedule": schedule
        })

    # --- Generate cases ---
    cases = []
    time = 9.0
    for i in range(num_cases):
        duration = random.choice([1.0, 1.5])
        case = {
            "name": f"Case_{i+1}",
            "time": round(time, 1),
            "senority": random.randint(1, 3),
            "location": random.choice(locations),
            "duration": duration,
        }
        cases.append(case)
        # Slightly stagger start times to reduce conflicts
        time += random.uniform(1.5, 2.5)

    return cases, barristers, travel_times


# --- Example usage ---
cases, barristers, travel_times = generate_consistent_test()


cases = [
    {"name": "Case01", "time": 9.0,  "senority": 1, "location": "Court1", "duration": 1.0},
    {"name": "Case02", "time": 9.5,  "senority": 2, "location": "Court2", "duration": 1.0},
    {"name": "Case03", "time": 10.0, "senority": 3, "location": "Court3", "duration": 1.5},
    {"name": "Case04", "time": 10.5, "senority": 1, "location": "Court4", "duration": 1.0},
    {"name": "Case05", "time": 11.0, "senority": 2, "location": "Court5", "duration": 1.0},
    {"name": "Case06", "time": 11.5, "senority": 1, "location": "Court1", "duration": 1.0},
    {"name": "Case07", "time": 12.0, "senority": 2, "location": "Court2", "duration": 1.0},
    {"name": "Case08", "time": 12.5, "senority": 3, "location": "Court3", "duration": 1.0},
    {"name": "Case09", "time": 13.0, "senority": 1, "location": "Court4", "duration": 1.0},
    {"name": "Case10", "time": 13.5, "senority": 2, "location": "Court5", "duration": 1.5},
    {"name": "Case11", "time": 14.0, "senority": 1, "location": "Court1", "duration": 1.0},
    {"name": "Case12", "time": 14.5, "senority": 3, "location": "Court2", "duration": 1.0},
    {"name": "Case13", "time": 15.0, "senority": 2, "location": "Court3", "duration": 1.0},
    {"name": "Case14", "time": 15.5, "senority": 1, "location": "Court4", "duration": 1.0},
    {"name": "Case15", "time": 16.0, "senority": 2, "location": "Court5", "duration": 1.0},
    {"name": "Case16", "time": 16.5, "senority": 3, "location": "Court1", "duration": 1.0},
    {"name": "Case17", "time": 17.0, "senority": 1, "location": "Court2", "duration": 1.0},
    {"name": "Case18", "time": 17.5, "senority": 2, "location": "Court3", "duration": 1.0},
    {"name": "Case19", "time": 18.0, "senority": 1, "location": "Court4", "duration": 1.0},
    {"name": "Case20", "time": 18.5, "senority": 2, "location": "Court5", "duration": 1.5},
    {"name": "Case21", "time": 9.3,  "senority": 1, "location": "Court2", "duration": 1.0},
    {"name": "Case22", "time": 10.8, "senority": 2, "location": "Court3", "duration": 1.0},
    {"name": "Case23", "time": 12.3, "senority": 1, "location": "Court4", "duration": 1.0},
    {"name": "Case24", "time": 13.8, "senority": 3, "location": "Court5", "duration": 1.0},
    {"name": "Case25", "time": 15.3, "senority": 1, "location": "Court1", "duration": 1.0},
    {"name": "Case26", "time": 16.8, "senority": 2, "location": "Court2", "duration": 1.0},
    {"name": "Case27", "time": 18.3, "senority": 1, "location": "Court3", "duration": 1.0},
    {"name": "Case28", "time": 9.7,  "senority": 2, "location": "Court4", "duration": 1.0},
    {"name": "Case29", "time": 11.2, "senority": 3, "location": "Court5", "duration": 1.0},
    {"name": "Case30", "time": 12.7, "senority": 1, "location": "Court1", "duration": 1.0},
    {"name": "Case31", "time": 14.2, "senority": 2, "location": "Court2", "duration": 1.0},
    {"name": "Case32", "time": 15.7, "senority": 3, "location": "Court3", "duration": 1.0},
    {"name": "Case33", "time": 17.2, "senority": 1, "location": "Court4", "duration": 1.0},
    {"name": "Case34", "time": 18.7, "senority": 2, "location": "Court5", "duration": 1.0},
    {"name": "Case35", "time": 9.9,  "senority": 1, "location": "Court1", "duration": 1.0},
    {"name": "Case36", "time": 11.4, "senority": 2, "location": "Court2", "duration": 1.0},
    {"name": "Case37", "time": 12.9, "senority": 3, "location": "Court3", "duration": 1.0},
    {"name": "Case38", "time": 14.4, "senority": 2, "location": "Court4", "duration": 1.0},
    {"name": "Case39", "time": 15.9, "senority": 1, "location": "Court5", "duration": 1.0},
    {"name": "Case40", "time": 17.4, "senority": 2, "location": "Court1", "duration": 1.0},
]

barristers = [
    {"name": "Alice", "senority": 3, "schedule": []},
    {"name": "Bob", "senority": 2, "schedule": []},
    {"name": "Charlie", "senority": 1, "schedule": []},
    {"name": "Diana", "senority": 2, "schedule": []},
    {"name": "Edward", "senority": 3, "schedule": []},
    {"name": "Fiona", "senority": 2, "schedule": []},
    {"name": "George", "senority": 1, "schedule": []},
    {"name": "Hannah", "senority": 3, "schedule": []},
    {"name": "Ian", "senority": 2, "schedule": []},
    {"name": "Julia", "senority": 1, "schedule": []},
    {"name": "Kevin", "senority": 3, "schedule": []},
    {"name": "Laura", "senority": 2, "schedule": []},
    {"name": "Mike", "senority": 1, "schedule": []},
    {"name": "Nina", "senority": 2, "schedule": []},
    {"name": "Oscar", "senority": 3, "schedule": []},
]

travel_times = {
    ("Court1", "Court1"): 0.0, ("Court1", "Court2"): 0.8, ("Court1", "Court3"): 1.1, ("Court1", "Court4"): 1.4, ("Court1", "Court5"): 0.9,
    ("Court2", "Court1"): 0.8, ("Court2", "Court2"): 0.0, ("Court2", "Court3"): 0.6, ("Court2", "Court4"): 1.0, ("Court2", "Court5"): 1.3,
    ("Court3", "Court1"): 1.1, ("Court3", "Court2"): 0.6, ("Court3", "Court3"): 0.0, ("Court3", "Court4"): 0.8, ("Court3", "Court5"): 1.0,
    ("Court4", "Court1"): 1.4, ("Court4", "Court2"): 1.0, ("Court4", "Court3"): 0.8, ("Court4", "Court4"): 0.0, ("Court4", "Court5"): 0.7,
    ("Court5", "Court1"): 0.9, ("Court5", "Court2"): 1.3, ("Court5", "Court3"): 1.0, ("Court5", "Court4"): 0.7, ("Court5", "Court5"): 0.0,
}

cases = []
# 45 cases, overlapping times
for i in range(45):
    cases.append({
        "name": f"Case{i+1}",
        "time": 9.0 + (i * 0.3),  # overlapping start times
        "senority": (i % 3) + 1,  # senority 1–3
        "location": f"Court{(i % 5) + 1}",  # 5 courts
        "duration": 1.0
    })

barristers = []
# 10 barristers with limited availability
for i in range(10):
    # Each barrister has 1–3 unavailable blocks
    schedule = []
    for j in range((i % 3) + 1):
        start = 9.0 + j * 3.0
        end = start + 1.5
        location = f"Court{((i+j) % 5) + 1}"
        schedule.append({"start_time": start, "end_time": end, "location": location})
    barristers.append({
        "name": f"Barrister_{i+1}",
        "senority": (i % 3) + 1,
        "schedule": schedule
    })

travel_times = {}
courts = [f"Court{i}" for i in range(1, 6)]
# travel times between courts: 0.5–1.5 hours
for c1 in courts:
    for c2 in courts:
        travel_times[(c1, c2)] = 0.5 + abs(int(c1[-1]) - int(c2[-1])) * 0.25

# Plug into your existing CSP pipeline:
variables, domains, constraints = define_inputs(cases, barristers, travel_times)
csp = CSP(variables, domains, constraints)

import time, tracemalloc
tracemalloc.start()
start_time = time.time()

print("running")
MRV_variables = sorted(csp.variables, key=lambda var: len(csp.domains[var]))
result = backtrack({}, csp, MRV_variables, 0, len(MRV_variables))
print("done")

end_time = time.time()
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"\nRuntime: {end_time - start_time:.4f} seconds")
print(f"Peak memory: {peak / 10**6:.2f} MB")
print(f"\nSolution: {result}")