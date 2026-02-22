
from algorithms.ortoolssolver3 import *

barristers = [
    {
        "name": "B0",
        "home": "A",
        "day_start": 540,   # 09:00
        "day_end": 1020,    # 17:00
        "seniority": 1,
        "schedule": [
            {"start_time": 660, "end_time": 720, "location": "A"}  # 11:00-12:00 blocked
        ],
    },
    {
        "name": "B1",
        "home": "D",
        "day_start": 540,
        "day_end": 1020,
        "seniority": 1,
        "schedule": [
            {"start_time": 780, "end_time": 840, "location": "D"}  # 13:00-14:00 blocked
        ],
    },
]

cases = [
    {"name": "C0", "time": 600, "duration": 45, "location": "B", "seniority": 1},  # 10:00-10:45
    {"name": "C1", "time": 690, "duration": 45, "location": "C", "seniority": 1},  # 11:30-12:15
    {"name": "C2", "time": 750, "duration": 45, "location": "C", "seniority": 1},  # 12:30-13:15
    {"name": "C3", "time": 870, "duration": 45, "location": "B", "seniority": 1},  # 14:30-15:15
]

travel_times = {
    ("A","A"):0, ("A","B"):10, ("A","C"):20, ("A","D"):30,
    ("B","A"):10, ("B","B"):0, ("B","C"):10, ("B","D"):20,
    ("C","A"):20, ("C","B"):10, ("C","C"):0, ("C","D"):10,
    ("D","A"):30, ("D","B"):20, ("D","C"):10, ("D","D"):0,
}

# all case costs zero (pure travel objective)
case_costs = {(c["name"], b["name"]): 0 for c in cases for b in barristers}
case_costs[("C0", "B1")] = 1

cases_sorted = sorted(cases, key=lambda c: c["time"])
model, assign, unassigned, cases_sorted, schedule = setup_model(
    cases_sorted,
    barristers,
    travel_times,
    case_costs,
)

result = solve_model(model, assign, unassigned, cases_sorted, schedule)

print(result)
