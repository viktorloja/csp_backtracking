from functions.md_loader import load_cases_from_folder, load_barristers_from_folder
from functions.llm_summary import process_folder_txt_to_md
from functions.generate_schedule import generate_schedule
from functions.html_output import render_schedule_html_from_barrister_events

def process(
    format,
    training,
    cases_path,
    barristers_path,
    travel_times,
    output,
    out_name
):

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

   
    # run all the solvers and gather results

    results = {}
    solvers = ["ortools", "backtrack", "greedy"]

    for solver in solvers:

        print(f"Running solver: "+solver)
        result = generate_schedule(
            method=solver,
            barristers=barristers,
            cases=cases,
            travel_times=travel_times,
            training=training,
        )


        schedule = result["schedule"]

        if not schedule:
            raise RuntimeError(solver+" solver returned no schedule.")

        # Render HTML

        output_path = output/ (out_name+"-"+solver+".html")

        html_path = render_schedule_html_from_barrister_events(
            schedule,
            title="Barrister Schedule",
            out_path=output_path,
        )

        print("HTML "+solver+"-schedule written to: "+output_path)
        results[solver] = result


    return results