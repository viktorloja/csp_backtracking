from md_loader import load_cases_from_folder, load_barristers_from_folder
from llm_summary import process_folder_txt_to_md
from generate_schedule import generate_schedule
from html_output import render_schedule_html_from_barrister_events

def process(
        format, training, cases_path, barristers_path, travel_times, output, out_name):
    
    travel_times = {("London", "Court2"): 60, ("Court2", "London"): 60, ("Court2", "Court2"): 0}

    if format == "txt":
        print("Running LLM summarisation...")
        process_folder_txt_to_md(cases_path, barristers_path, cases_path, barristers_path)

    # Load markdown
    cases = load_cases_from_folder(cases_path)
    barristers = load_barristers_from_folder(barristers_path)

    print(f"Loaded {len(cases)} cases")
    print(f"Loaded {len(barristers)} barristers")

    if not cases:
        raise RuntimeError("No cases loaded.")
    if not barristers:
        raise RuntimeError("No barristers loaded.")

    # travel times

    #print(cases)
    #print(barristers)
    #print(travel_times)
    # run solver
    print(f"Running solver: backtracking")
    backtrack_result = generate_schedule(
        method="ortools",
        barristers=barristers,
        cases=cases,
        travel_times=travel_times,
        training=training,
    )

    print(f"Running solver: ortoolssolver")
    ortools_result = generate_schedule(
        method="ortools",
        barristers=barristers,
        cases=cases,
        travel_times=travel_times,
        training=training,
    )
     

    backtrack_schedule = backtrack_result.get("schedule")
    backtrack_objective = backtrack_result.get("objective")
    backtrack_status = backtrack_result.get("status")

    ortools_schedule = ortools_result.get("schedule")
    ortools_objective = ortools_result.get("objective")
    ortools_status = ortools_result.get("status")

    if not backtrack_schedule:
        raise RuntimeError("Backtracking solver returned no schedule.")
    
    if not ortools_schedule:
        raise RuntimeError("Ortools solver returned no schedule")


    # Render HTML
   # os.makedirs(os.path.dirname(args.out), exist_ok=True)

    backtrack_output = output/ (out_name+"-backtracking.html")

    backtrack_path = render_schedule_html_from_barrister_events(
        backtrack_schedule,
        title="Barrister Schedule",
        out_path=backtrack_output,
    )

    ortools_output = output/ (out_name+"-ortools.html")

    ortools_path = render_schedule_html_from_barrister_events(
        ortools_schedule,
        title="Barrister Schedule",
        out_path=ortools_output,
    )

    print("HTML backtrack-schedule written to:", backtrack_path)
    print("HTML ortools-schedule written to:", ortools_path)


    return backtrack_objective, backtrack_status, ortools_objective, ortools_status