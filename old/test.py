from backtrack import CSP
from backtrack import branch_and_bound
from backtrack import define_inputs
from backtrack import best_solution
from backtrack import best_sol
from ortoolssolver import setup_ortools_model
from ortoolssolver import solve_ortools_model
import time, tracemalloc

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

# assign best possible barristers
def calculate_costs_optimal(cases, barristers):
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

# prioritising assigning inexperienced barristers for training on insevere cases
def calculate_costs_balanced(cases, barristers):
    case_costs = {}
    for case in cases:
        for barrister in barristers:
            cost = 700
            if case["type"] in barrister["expertise"]:
                cost -= 200
            if not case["severe"] and barrister["experience"] < 3: # case not too severe so can be used for training
                cost -= 300 # heavily prioritised inexperienced barristers to give training opportunities
            else:
                cost -= min(200, barrister["experience"]*10)
            cost -= 200*barrister["winrate"]
            case_costs[(case["name"], barrister["name"])] = cost

    return case_costs
                



def evaluate(cases, barristers, best_solution):
    scores = {}
    locations = {}
    for barrister in barristers:
        name = barrister["name"]
        scores[name] = 0
        locations[name] = barrister["home"]

    for case in cases:
        casename = case["name"]
        if casename in best_solution:
            barrister = best_solution[casename] 
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
                training=False,
                **kwargs):

    """
    Solve the case assignment problem using the chosen method.
    
    method options:
        - "ortools"
        - "backtracking"
    """
    
    output = {}
    cases_sorted = sorted(cases, key=lambda c: c["time"])
    if training:
        case_costs = calculate_costs_balanced(cases_sorted, barristers)
    else:
        case_costs = calculate_costs_optimal(cases_sorted, barristers)

    if method == "ortools":

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
        
        output["result"] = result["assignment"]
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6
        output["fairness"] = evaluate(cases_sorted, barristers, result["assignment"])

    elif method == "backtracking":

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
        output["fairness"] = evaluate(cases_sorted, barristers, best_sol())



    else:
        raise ValueError(f"Unknown method: {method}")

    return output

import random

random.seed(2)

# --------------------------------------
# LOCATIONS
# --------------------------------------
locations = [f"L{i}" for i in range(20)]

travel_times = {}
for i in range(len(locations)-1):
    for j in range(i, len(locations)):
        a = locations[i]
        b = locations[j]
        if a == b:
            travel_times[(a,b)] = 0
        else:
            timee = random.randint(5,60)
            travel_times[(a,b)] = timee
            travel_times[(b,a)] = timee

# --------------------------------------
# BARRISTERS
# --------------------------------------
barristers = []
for i in range(18):
    schedules = []
    # 1–3 availability blocks
    for _ in range(random.randint(1, 3)):
        s = random.randint(80, 300)
        schedules.append({
            "start_time": s,
            "end_time": s + random.randint(60, 180),
            "location": random.choice(locations)
        })
    barristers.append({
        "name": f"B{i}",
        "home": random.choice(locations),
        "seniority": random.randint(0, 8),
        "expertise": random.sample(["criminal", "family", "civil", "commercial", "employment"], k=3),
        "experience": random.randint(0, 30),
        "winrate": round(random.random(), 2),
        "schedule": schedules
    })

# --------------------------------------
# CASES
# --------------------------------------
cases = []
t = 0
for i in range(60):
    start = t + random.randint(0, 30)
    duration = random.randint(20, 90)
    t = start
    cases.append({
        "name": f"C{i}",
        "type": random.choice(["criminal", "family", "civil", "commercial", "employment"]),
        "time": start,
        "duration": duration,
        "location": random.choice(locations),
        "seniority": random.randint(0, 8)
    })

locations = ["A", "B", "C", "D", "E"]

travel_times = {
    ("A","A"):0, ("A","B"):10, ("A","C"):15, ("A","D"):20, ("A","E"):25,
    ("B","A"):10, ("B","B"):0, ("B","C"):10, ("B","D"):20, ("B","E"):30,
    ("C","A"):15, ("C","B"):10, ("C","C"):0, ("C","D"):10, ("C","E"):20,
    ("D","A"):20, ("D","B"):20, ("D","C"):10, ("D","D"):0, ("D","E"):15,
    ("E","A"):25, ("E","B"):30, ("E","C"):20, ("E","D"):15, ("E","E"):0,
}

barristers = [
    {
        "name": "B0",
        "home": "A",
        "seniority": 3,
        "expertise": ["criminal", "civil"],
        "experience": 10,
        "winrate": 0.4,
        "schedule": []   # fully free
    },
    {
        "name": "B1",
        "home": "B",
        "seniority": 4,
        "expertise": ["family", "criminal"],
        "experience": 6,
        "winrate": 0.3,
        "schedule": []
    },
    {
        "name": "B2",
        "home": "C",
        "seniority": 2,
        "expertise": ["civil", "commercial"],
        "experience": 3,
        "winrate": 0.2,
        "schedule": []
    }
]

cases = [
    {
        "name": "C0",
        "type": "criminal",
        "time": 0,
        "duration": 30,
        "location": "A",
        "seniority": 1
    },
    {
        "name": "C1",
        "type": "family",
        "time": 60,
        "duration": 30,
        "location": "B",
        "seniority": 1
    },
    {
        "name": "C2",
        "type": "civil",
        "time": 120,
        "duration": 30,
        "location": "C",
        "seniority": 2
    },
    {
        "name": "C3",
        "type": "commercial",
        "time": 180,
        "duration": 30,
        "location": "D",
        "seniority": 1
    },
    {
        "name": "C4",
        "type": "criminal",
        "time": 240,
        "duration": 30,
        "location": "A",
        "seniority": 2
    }
]

locations = ["A","B","C","D","E","F","G","H","I","J"]

travel_times = {}
for a in locations:
    for b in locations:
        if a == b:
            travel_times[(a,b)] = 0
        else:
            # Maximum travel time = 20 minutes
            travel_times[(a,b)] = 10 + (abs(ord(a)-ord(b)) % 10)

locations = ["A","B","C","D","E","F","G","H","I","J"]
# Create a symmetric travel matrix
base_times = [
    [0, 10, 12, 14, 16, 18, 17, 15, 13, 11],
    [10, 0,  9, 11, 13, 15, 16, 14, 12, 10],
    [12, 9,  0,  8, 10, 12, 14, 16, 15, 13],
    [14,11, 8,  0,  7,  9, 11, 13, 14, 16],
    [16,13,10, 7,  0,  6,  8, 10, 12, 14],
    [18,15,12, 9,  6,  0,  5,  7,  9, 11],
    [17,16,14,11, 8,  5,  0,  6,  8, 10],
    [15,14,16,13,10, 7,  6,  0,  5,  7],
    [13,12,15,14,12, 9,  8,  5,  0,  6],
    [11,10,13,16,14,11,10, 7,  6,  0]
]

travel_times = {}
for i, a in enumerate(locations):
    for j, b in enumerate(locations):
        travel_times[(a,b)] = base_times[i][j]

barristers = [
    {"name":"B0","home":"A","seniority":5,"expertise":["criminal","family","civil"],"experience":10,"winrate":0.4,"schedule":[]},
    {"name":"B1","home":"B","seniority":4,"expertise":["civil","commercial","family"],"experience":8,"winrate":0.35,"schedule":[]},
    {"name":"B2","home":"C","seniority":6,"expertise":["criminal","employment"],"experience":7,"winrate":0.25,"schedule":[]},
    {"name":"B3","home":"D","seniority":5,"expertise":["commercial","civil"],"experience":12,"winrate":0.50,"schedule":[]},
    {"name":"B4","home":"E","seniority":7,"expertise":["criminal","family","immigration"],"experience":6,"winrate":0.22,"schedule":[]},
    {"name":"B5","home":"F","seniority":3,"expertise":["civil","commercial","employment"],"experience":5,"winrate":0.28,"schedule":[]},
    {"name":"B6","home":"G","seniority":4,"expertise":["family","immigration"],"experience":9,"winrate":0.31,"schedule":[]},
    {"name":"B7","home":"H","seniority":8,"expertise":["criminal","commercial"],"experience":11,"winrate":0.45,"schedule":[]}
]
case_types = ["criminal","family","civil","commercial","employment","immigration"]

cases = []
timee = 0
loc_cycle = ["A","B","C","D","E","F","G","H","I","J"]

for i in range(40):
    cases.append({
        "name": f"C{i}",
        "type": case_types[i % len(case_types)],
        "time": timee,
        "duration": 30,
        "location": loc_cycle[i % len(loc_cycle)],
        "seniority": (i % 3)
    })
    timee += 45

res = solve_cases(cases, barristers, travel_times, method="backtracking")
print(res)
print(len(res["result"]))
res = solve_cases(cases, barristers, travel_times)
print(res)
print(len(res["result"]))


# barrister case history
# different cost functions, weigh different things, e.g. optimize for experience, winrate?
# optimize for training?
# cost function to give more experience to junior barristers on non-critical cases
# refactor code to run input with multiple different cost functions, then surface results for human evaluation

# christmas
# optimize functions more
# nlp to convert case textfile -> markdown info file
# schedule visualization?
# sketch UI / frontend - email for feedback over holiday
# typescript?
# clerk evaluation