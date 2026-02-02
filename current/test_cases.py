from generate_schedule import generate_schedule
from html_output import render_schedule_html_from_barrister_events

# -------------------------
# Feasible test data
# -------------------------

cases = [
    {
        "name": "CaseA",
        "time": 9*60,          # 09:00
        "duration": 60,        # 1h
        "location": "Court1",
        "seniority": 1,
        "type": "criminal",
        "subtype": None,
        "court": "Court1",
        "experience_required": [],
        "risk_level": None,
        "notes": "## Summary\nSimple hearing.",
        "_source_file": "data/cases/case_a.md",
    },
    {
        "name": "CaseB",
        "time": 10*60 + 30,     # 10:30
        "duration": 60,         # 1h
        "location": "Court2",
        "seniority": 1,
        "type": "civil",
        "subtype": None,
        "court": "Court2",
        "experience_required": [],
        "risk_level": None,
        "notes": "## Summary\nAnother hearing.",
        "_source_file": "data/cases/case_b.md",
    },
    {
        "name": "CaseC",
        "time": 12*60 + 0,      # 12:00
        "duration": 60,         # 1h
        "location": "Court1",
        "seniority": 2,
        "type": "criminal",
        "subtype": None,
        "court": "Court1",
        "experience_required": [],
        "risk_level": None,
        "notes": "## Summary\nSlightly more senior case.",
        "_source_file": "data/cases/case_c.md",
    },
]

barristers = [
    {
        "name": "Alice Khan",
        "seniority": 3,
        "home": "London",
        "schedule": [],  # no mandatory blocks
        "expertise": ["criminal", "civil"],
        "courts": [],
        "locations": [],
        "winrate": 0.43,
        "experience": 13,
        "notes": "## Profile\nGeneralist.",
        "_source_file": "data/barristers/alice_khan.md",
    },
    {
        "name": "Ben Carter",
        "seniority": 2,
        "home": "London",
        "schedule": [],  # no mandatory blocks
        "expertise": ["criminal"],
        "courts": [],
        "locations": [],
        "winrate": 0.53,
        "experience": 5,
        "notes": "## Profile\nCriminal focus.",
        "_source_file": "data/barristers/ben_carter.md",
    },
]

# Symmetric travel times with 0 diagonal
travel_times = {
    ("Court1", "Court1"): 0,
    ("Court2", "Court2"): 0,
    ("London", "London"): 0,

    ("Court1", "Court2"): 20,
    ("Court2", "Court1"): 20,

    ("London", "Court1"): 30,
    ("Court1", "London"): 30,

    ("London", "Court2"): 35,
    ("Court2", "London"): 35,
}



output = generate_schedule(cases, barristers, travel_times)
print(output)

schedule = {
    "Alice Khan": [
        [540, 600, "Block: Conference", "Court2"],
        [630, 720, "CaseA", "Court1"],
        [735, 780, "Travel buffer / Admin", "Chambers"],
    ],
    "Ben Carter": [
        [600, 660, "CaseB", "Court2"],
        [720, 780, "CaseC", "Court2"],
    ],
}

path = render_schedule_html_from_barrister_events(schedule, out_path="data/outputs/schedule.html")
print("Wrote:", path)