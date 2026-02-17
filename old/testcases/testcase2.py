# HEAVILY CONFLICTED

cases = [
    {"name": "C1", "time": 9.0,  "seniority": 8, "location": "Court_A", "duration": 2.0},
    {"name": "C2", "time": 9.0,  "seniority": 4, "location": "Court_B", "duration": 1.5},
    {"name": "C3", "time": 9.5,  "seniority": 6, "location": "Court_C", "duration": 2.0},
    {"name": "C4", "time": 10.0, "seniority": 2, "location": "Court_A", "duration": 1.0},
    {"name": "C5", "time": 10.0, "seniority": 7, "location": "Court_D", "duration": 1.5},
    {"name": "C6", "time": 10.5, "seniority": 5, "location": "Court_E", "duration": 2.0},
    {"name": "C7", "time": 10.5, "seniority": 3, "location": "Court_B", "duration": 1.0},
    {"name": "C8", "time": 11.0, "seniority": 9, "location": "Court_C", "duration": 1.5},
    {"name": "C9", "time": 11.0, "seniority": 4, "location": "Court_D", "duration": 2.0},
    {"name": "C10", "time": 11.5, "seniority": 6, "location": "Court_E", "duration": 1.0},

    {"name": "C11", "time": 12.0, "seniority": 3, "location": "Court_A", "duration": 1.5},
    {"name": "C12", "time": 12.0, "seniority": 8, "location": "Court_B", "duration": 1.0},
    {"name": "C13", "time": 12.5, "seniority": 2, "location": "Court_C", "duration": 2.0},
    {"name": "C14", "time": 12.5, "seniority": 5, "location": "Court_D", "duration": 1.5},
    {"name": "C15", "time": 13.0, "seniority": 7, "location": "Court_E", "duration": 2.0},

    {"name": "C16", "time": 13.0, "seniority": 3, "location": "Court_A", "duration": 1.0},
    {"name": "C17", "time": 13.5, "seniority": 4, "location": "Court_B", "duration": 1.5},
    {"name": "C18", "time": 13.5, "seniority": 9, "location": "Court_C", "duration": 2.0},
    {"name": "C19", "time": 14.0, "seniority": 6, "location": "Court_D", "duration": 1.0},
    {"name": "C20", "time": 14.0, "seniority": 8, "location": "Court_E", "duration": 2.0},

    {"name": "C21", "time": 14.5, "seniority": 2, "location": "Court_A", "duration": 1.5},
    {"name": "C22", "time": 14.5, "seniority": 7, "location": "Court_B", "duration": 1.0},
    {"name": "C23", "time": 15.0, "seniority": 5, "location": "Court_C", "duration": 2.0},
    {"name": "C24", "time": 15.0, "seniority": 9, "location": "Court_D", "duration": 1.5},
    {"name": "C25", "time": 15.0, "seniority": 3, "location": "Court_E", "duration": 1.0},
]

barristers = [
    {
        "name": "B1", "seniority": 10, "home": "Home_X",
        "schedule": [
            {"start_time": 8.0, "end_time": 9.5, "location": "Court_A"},
            {"start_time": 12.0, "end_time": 13.0, "location": "Court_D"},
        ],
    },
    {
        "name": "B2", "seniority": 8, "home": "Home_Y",
        "schedule": [
            {"start_time": 9.0,  "end_time": 10.0, "location": "Court_B"},
            {"start_time": 11.5, "end_time": 12.5, "location": "Court_C"},
        ],
    },
    {
        "name": "B3", "seniority": 7, "home": "Home_Z",
        "schedule": [
            {"start_time": 10.0, "end_time": 11.0, "location": "Court_A"},
            {"start_time": 13.0, "end_time": 14.0, "location": "Court_B"},
        ],
    },
    {
        "name": "B4", "seniority": 9, "home": "Home_W",
        "schedule": [
            {"start_time": 9.5, "end_time": 11.0, "location": "Court_C"},
        ],
    },
    {
        "name": "B5", "seniority": 6, "home": "Home_Q",
        "schedule": [
            {"start_time": 11.0, "end_time": 12.5, "location": "Court_E"},
        ],
    },
    {
        "name": "B6", "seniority": 5, "home": "Home_R",
        "schedule": [
            {"start_time": 10.0, "end_time": 11.0, "location": "Court_D"},
            {"start_time": 14.0, "end_time": 15.0, "location": "Court_A"},
        ],
    },
    {
        "name": "B7", "seniority": 4, "home": "Home_S",
        "schedule": [
            {"start_time": 12.0, "end_time": 13.0, "location": "Court_C"},
        ],
    },
    {
        "name": "B8", "seniority": 3, "home": "Home_T",
        "schedule": [
            {"start_time": 9.0, "end_time": 10.5, "location": "Court_E"},
        ],
    },
    {
        "name": "B9", "seniority": 2, "home": "Home_U",
        "schedule": [
            {"start_time": 13.5, "end_time": 14.5, "location": "Court_B"},
        ],
    },
    {
        "name": "B10", "seniority": 7, "home": "Home_V",
        "schedule": [],
    },
    {
        "name": "B11", "seniority": 5, "home": "Home_M",
        "schedule": [
            {"start_time": 9.0, "end_time": 10.0, "location": "Court_D"},
            {"start_time": 12.5, "end_time": 13.5, "location": "Court_E"},
        ],
    },
    {
        "name": "B12", "seniority": 9, "home": "Home_N",
        "schedule": [
            {"start_time": 11.0, "end_time": 12.0, "location": "Court_B"},
        ],
    },
]

travel_times = {}
locations = [
    "Court_A", "Court_B", "Court_C", "Court_D", "Court_E",
    "Home_X", "Home_Y", "Home_Z", "Home_W",
    "Home_Q", "Home_R", "Home_S", "Home_T", "Home_U", "Home_V",
    "Home_M", "Home_N"
]

import itertools
for a, b in itertools.combinations_with_replacement(locations, 2):
    if a == b:
        t = 0.0
    else:
        t = 0.3 + (abs(hash(tuple(sorted([a, b])))) % 120) / 100
    
    travel_times[(a, b)] = t
    travel_times[(b, a)] = t
