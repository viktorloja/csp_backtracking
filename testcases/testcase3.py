# PARTIAL ASSIGNMENT

cases = [
    # --- MORNING CLUSTER (overlapping heavily) ---
    {"name": "C1",  "time": 9.00, "duration": 1.0, "location": "Court_A", "seniority": 5},
    {"name": "C2",  "time": 9.10, "duration": 1.0, "location": "Court_B", "seniority": 9},  # HIGH
    {"name": "C3",  "time": 9.20, "duration": 1.5, "location": "Court_C", "seniority": 3},
    {"name": "C4",  "time": 9.30, "duration": 1.0, "location": "Court_D", "seniority": 7},
    {"name": "C5",  "time": 9.40, "duration": 1.0, "location": "Court_E", "seniority": 10}, # HIGH
    {"name": "C6",  "time": 9.50, "duration": 1.0, "location": "Court_F", "seniority": 6},

    # --- MIDDAY CLASH (unavoidable triple overlap) ---
    {"name": "C7",  "time": 11.00, "duration": 1.0, "location": "Court_A", "seniority": 9},
    {"name": "C8",  "time": 11.05, "duration": 1.0, "location": "Court_B", "seniority": 8},
    {"name": "C9",  "time": 11.10, "duration": 1.0, "location": "Court_C", "seniority": 2},

    # --- AFTERNOON NARROW WINDOWS ---
    {"name": "C10", "time": 13.00, "duration": 1.0, "location": "Court_A", "seniority": 10},
    {"name": "C11", "time": 13.10, "duration": 1.0, "location": "Court_B", "seniority": 4},
    {"name": "C12", "time": 13.20, "duration": 1.0, "location": "Court_C", "seniority": 9},
    {"name": "C13", "time": 13.30, "duration": 1.0, "location": "Court_D", "seniority": 6},
    {"name": "C14", "time": 13.40, "duration": 1.0, "location": "Court_E", "seniority": 1},

    # --- LATE AFTERNOON (multiple high-seniority bottlenecks) ---
    {"name": "C15", "time": 15.00, "duration": 1.0, "location": "Court_A", "seniority": 10},
    {"name": "C16", "time": 15.05, "duration": 1.0, "location": "Court_B", "seniority": 9},
    {"name": "C17", "time": 15.10, "duration": 1.0, "location": "Court_C", "seniority": 8},
    {"name": "C18", "time": 15.15, "duration": 1.0, "location": "Court_D", "seniority": 7},
    {"name": "C19", "time": 15.20, "duration": 1.0, "location": "Court_E", "seniority": 6},
    {"name": "C20", "time": 15.25, "duration": 1.0, "location": "Court_F", "seniority": 10},
]

barristers = [

    # --- Senior barristers (only 3!) ---
    {
        "name": "B1", "seniority": 10, "home": "Home_A",
        "schedule": [
            {"start_time": 8.50, "end_time": 10.00, "location": "Court_A"},
            {"start_time": 14.00, "end_time": 15.00, "location": "Court_D"},
        ],
    },
    {
        "name": "B2", "seniority": 9, "home": "Home_B",
        "schedule": [
            {"start_time": 9.00, "end_time": 11.00, "location": "Court_C"},
            {"start_time": 13.00, "end_time": 14.00, "location": "Court_B"},
        ],
    },
    {
        "name": "B3", "seniority": 9, "home": "Home_C",
        "schedule": [
            {"start_time": 11.00, "end_time": 12.00, "location": "Court_E"},
        ],
    },

    # --- Mid-level ---
    {
        "name": "B4", "seniority": 8, "home": "Home_D",
        "schedule": [
            {"start_time": 9.50, "end_time": 10.50, "location": "Court_B"},
        ],
    },
    {
        "name": "B5", "seniority": 7, "home": "Home_E",
        "schedule": [
            {"start_time": 9.30, "end_time": 11.00, "location": "Court_D"},
        ],
    },
    {
        "name": "B6", "seniority": 6, "home": "Home_F",
        "schedule": [],
    },
    {
        "name": "B7", "seniority": 6, "home": "Home_G",
        "schedule": [
            {"start_time": 14.00, "end_time": 15.00, "location": "Court_F"},
        ],
    },

    # --- Lower seniority ---
    {
        "name": "B8", "seniority": 4, "home": "Home_H",
        "schedule": [],
    },
    {
        "name": "B9", "seniority": 3, "home": "Home_I",
        "schedule": [
            {"start_time": 13.00, "end_time": 14.00, "location": "Court_E"},
        ],
    },
    {
        "name": "B10", "seniority": 2, "home": "Home_J",
        "schedule": [],
    },
    {
        "name": "B11", "seniority": 1, "home": "Home_K",
        "schedule": [
            {"start_time": 15.00, "end_time": 16.00, "location": "Court_A"},
        ],
    },
    {
        "name": "B12", "seniority": 1, "home": "Home_L",
        "schedule": [],
    },
]

travel_times = {
    # Court → Court (too long to chain anything: 1.0h)
    ("Court_A","Court_B"):1.0, ("Court_B","Court_A"):1.0,
    ("Court_A","Court_C"):1.0, ("Court_C","Court_A"):1.0,
    ("Court_A","Court_D"):1.0, ("Court_D","Court_A"):1.0,
    ("Court_A","Court_E"):1.0, ("Court_E","Court_A"):1.0,
    ("Court_A","Court_F"):1.0, ("Court_F","Court_A"):1.0,

    ("Court_B","Court_C"):1.0, ("Court_C","Court_B"):1.0,
    ("Court_B","Court_D"):1.0, ("Court_D","Court_B"):1.0,
    ("Court_B","Court_E"):1.0, ("Court_E","Court_B"):1.0,
    ("Court_B","Court_F"):1.0, ("Court_F","Court_B"):1.0,

    ("Court_C","Court_D"):1.0, ("Court_D","Court_C"):1.0,
    ("Court_C","Court_E"):1.0, ("Court_E","Court_C"):1.0,
    ("Court_C","Court_F"):1.0, ("Court_F","Court_C"):1.0,

    ("Court_D","Court_E"):1.0, ("Court_E","Court_D"):1.0,
    ("Court_D","Court_F"):1.0, ("Court_F","Court_D"):1.0,

    ("Court_E","Court_F"):1.0, ("Court_F","Court_E"):1.0,

    # Home → Court (reasonable but fixed)
    ("Home_A","Court_A"):0.3, ("Court_A","Home_A"):0.3,
    ("Home_A","Court_B"):0.4, ("Court_B","Home_A"):0.4,
    ("Home_A","Court_C"):0.6, ("Court_C","Home_A"):0.6,
    ("Home_A","Court_D"):0.5, ("Court_D","Home_A"):0.5,
    ("Home_A","Court_E"):0.6, ("Court_E","Home_A"):0.6,
    ("Home_A","Court_F"):0.7, ("Court_F","Home_A"):0.7,

    ("Home_B","Court_A"):0.4, ("Court_A","Home_B"):0.4,
    ("Home_B","Court_B"):0.3, ("Court_B","Home_B"):0.3,
    ("Home_B","Court_C"):0.4, ("Court_C","Home_B"):0.4,
    ("Home_B","Court_D"):0.7, ("Court_D","Home_B"):0.7,
    ("Home_B","Court_E"):0.8, ("Court_E","Home_B"):0.8,
    ("Home_B","Court_F"):0.9, ("Court_F","Home_B"):0.9,

    ("Home_C","Court_A"):0.5, ("Court_A","Home_C"):0.5,
    ("Home_C","Court_B"):0.4, ("Court_B","Home_C"):0.4,
    ("Home_C","Court_C"):0.3, ("Court_C","Home_C"):0.3,
    ("Home_C","Court_D"):0.6, ("Court_D","Home_C"):0.6,
    ("Home_C","Court_E"):0.6, ("Court_E","Home_C"):0.6,
    ("Home_C","Court_F"):0.7, ("Court_F","Home_C"):0.7,

    # similar for other homes (not needed if those barristers rarely move)
}

