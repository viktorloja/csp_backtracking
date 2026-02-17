import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def visualize_schedule(cases, assignment, travel_times):

    barrister_schedule = {}
    for case in cases:
        cname = case["name"]
        if cname not in assignment:
            continue 
        bname = assignment[cname]
        barrister_schedule.setdefault(bname, []).append(case)

    for b in barrister_schedule:
        barrister_schedule[b].sort(key=lambda x: x["time"])

    fig, ax = plt.subplots(figsize=(10, 5))
    y_ticks = []
    y_labels = []

    colors = plt.cm.tab20.colors
    color_map = {}

    for i, (bname, case_list) in enumerate(barrister_schedule.items()):
        y = i
        y_ticks.append(y)
        y_labels.append(bname)

        for j, case in enumerate(case_list):
            start = case["time"]
            duration = case["duration"]
            cname = case["name"]
            loc = case["location"]

            if cname not in color_map:
                color_map[cname] = colors[len(color_map) % len(colors)]

            ax.barh(
                y=y,
                width=duration,
                left=start,
                color=color_map[cname],
                edgecolor="black",
                height=0.4,
            )

            ax.text(
                start + duration / 2,
                y,
                f"{cname}\n{loc}",
                ha="center",
                va="center",
                fontsize=9,
                color="white",
                weight="bold",
            )

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Barrister")
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels)
    ax.set_title("Court Schedule - Barrister Assignments")
    ax.grid(True, axis='x', linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.show()

best_solution = {
    "Case1": "Charlie",
    "Case2": "Bob",
    "Case3": "Alice"
}

# Example case data
cases = [
    {"name": "Case1", "time": 9, "duration": 2, "senority": 2, "location": "London"},
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

visualize_schedule(cases, best_solution, travel_times)