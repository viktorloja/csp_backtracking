# MARKDOWN FILES

cases = [
    {"name": "C1", "time": 9.0,  "seniority": 8, "location": "Court_A", "duration": 2.0},
    {"name": "C2", "time": 10.0, "seniority": 2, "location": "Court_B", "duration": 1.0},
    {"name": "C3", "time": 11.0, "seniority": 6, "location": "Court_A", "duration": 1.5},
    {"name": "C4", "time": 9.5,  "seniority": 4, "location": "Court_C", "duration": 2.0},
    {"name": "C5", "time": 11.5, "seniority": 3, "location": "Court_B", "duration": 1.0},
]

barristers = [
    {
        "name": "B1",
        "seniority": 10,
        "home": "Home_X",
        "schedule": [
            {"start_time": 8.0, "end_time": 9.0, "location": "Court_A"},
            {"start_time": 11.5, "end_time": 13.0, "location": "Court_C"},
        ],
    },
    {
        "name": "B2",
        "seniority": 5,
        "home": "Home_Y",
        "schedule": [
            {"start_time": 9.0, "end_time": 10.0, "location": "Court_B"},
            {"start_time": 12.0, "end_time": 13.5, "location": "Court_B"},
        ],
    },
    {
        "name": "B3",
        "seniority": 7,
        "home": "Home_Z",
        "schedule": [
            {"start_time": 10.0, "end_time": 11.0, "location": "Court_A"},
        ],
    },
    {
        "name": "B4",
        "seniority": 3,
        "home": "Home_W",
        "schedule": [],  # completely free
    },
]

travel_times = {
    ("Court_A","Court_A"):0, ("Court_A","Court_B"):0.5, ("Court_A","Court_C"):0.7,
    ("Court_A","Home_X"):0.4, ("Court_A","Home_Y"):0.6, ("Court_A","Home_Z"):0.5, ("Court_A","Home_W"):0.8,

    ("Court_B","Court_A"):0.5, ("Court_B","Court_B"):0, ("Court_B","Court_C"):0.4,
    ("Court_B","Home_X"):0.7, ("Court_B","Home_Y"):0.3, ("Court_B","Home_Z"):0.6, ("Court_B","Home_W"):0.9,

    ("Court_C","Court_A"):0.7, ("Court_C","Court_B"):0.4, ("Court_C","Court_C"):0,
    ("Court_C","Home_X"):0.6, ("Court_C","Home_Y"):0.7, ("Court_C","Home_Z"):0.8, ("Court_C","Home_W"):1.0,

    ("Home_X","Court_A"):0.4, ("Home_X","Court_B"):0.7, ("Home_X","Court_C"):0.6,
    ("Home_X","Home_X"):0, ("Home_X","Home_Y"):1.0, ("Home_X","Home_Z"):0.9, ("Home_X","Home_W"):1.2,

    ("Home_Y","Court_A"):0.6, ("Home_Y","Court_B"):0.3, ("Home_Y","Court_C"):0.7,
    ("Home_Y","Home_X"):1.0, ("Home_Y","Home_Y"):0, ("Home_Y","Home_Z"):0.5, ("Home_Y","Home_W"):1.1,

    ("Home_Z","Court_A"):0.5, ("Home_Z","Court_B"):0.6, ("Home_Z","Court_C"):0.8,
    ("Home_Z","Home_X"):0.9, ("Home_Z","Home_Y"):0.5, ("Home_Z","Home_Z"):0, ("Home_Z","Home_W"):1.0,

    ("Home_W","Court_A"):0.8, ("Home_W","Court_B"):0.9, ("Home_W","Court_C"):1.0,
    ("Home_W","Home_X"):1.2, ("Home_W","Home_Y"):1.1, ("Home_W","Home_Z"):1.0, ("Home_W","Home_W"):0,
}
