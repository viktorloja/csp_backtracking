import argparse
from pathlib import Path

from processing.pipeline import process

def main():
    parser = argparse.ArgumentParser(
        description="Barrister scheduling pipeline"
    )

    parser.add_argument(
        "--format",
        choices=["md", "txt"],
        default="md",
        help="Input format: md = read markdown, txt = summarise text then read markdown",
    )

    parser.add_argument(
        "--solver",
        choices=["ortools", "backtrack"],
        default="ortools",
        help="Solver method (e.g. ortools, backtrack)",
    )

    parser.add_argument(
        "--input",
        default="data",
        help="Folder containing markdown or txt files or folder containing the scenario folders",
    )

    parser.add_argument(
        "--travel",
        default=None,
        help="Optional travel_times.py / json loader handled elsewhere",
    )

    parser.add_argument(
        "--output",
        default="data/outputs",
        help="Output HTML file path",
    )

    parser.add_argument(
        "--training",
        action="store_true",
        help="Enable training mode to prioritize lower experience barristers",
    )

    parser.add_argument(
        "--multiple",
        action="store_true",
        help="Enable multiple mode to do multiple scenarios and plot graphs",
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if args.multiple:
        print("mul")
        #print(args.cases)
        
        print(input_path)
        results = []

        for d in input_path.iterdir():
            if d.is_dir():
                if (d / "cases").is_dir() and (d / "barristers").is_dir():
                    name = "schedule-" + str(d)
                    if args.training:
                        name += "t"
                    result = process(
                        format = args.format,
                        training = args.training,
                        cases_path= d/ "cases",
                        barristers_path= d / "barristers",
                        travel_times= args.travel,
                        output= Path(args.output),
                        out_name= name,
                    )
                    results.append(result)

        #plot_graph(results, args.output)

    else:
        print("single")

        name = "schedule"
        if args.training:
            name += "t"

        result = process(
            format = args.format,
            training = args.training,
            cases_path= input_path/ "cases",
            barristers_path= input_path/ "barristers",
            travel_times= args.travel,
            output= Path(args.output),
            out_name= name,
        )

        print(result)
        









    

"""
# example usage
for scenario_dir in iter_subfolders("scenarios"):
    print("Scenario:", scenario_dir.name)




    
    if args.format == "txt":
        print("Running LLM summarisation...")
        process_folder_txt_to_md(args.cases, args.barristers, args.cases, args.barristers)

    # Load markdown
    cases = load_cases_from_folder(args.cases)
    barristers = load_barristers_from_folder(args.barristers)

    print(f"Loaded {len(cases)} cases")
    print(f"Loaded {len(barristers)} barristers")

    if not cases:
        raise RuntimeError("No cases loaded.")
    if not barristers:
        raise RuntimeError("No barristers loaded.")

    # travel times
    travel_times = {}

    print(cases)
    print(barristers)
    # run solver
    print(f"Running solver: {args.solver}")
    result = generate_schedule(
        method=args.solver,
        barristers=barristers,
        cases=cases,
        travel_times=travel_times,
        training=args.training,
    )

    """
"""
    Expected `result` format:
    {
        "schedule": {
            "Barrister Name": [
                [start, end, name, location],
                ...
            ],
            ...
        },
        "objective": float | None,
        "status": str
    }
    """
"""

    schedule = result.get("schedule")
    objective = result.get("objective")
    status = result.get("status")

    if not schedule:
        raise RuntimeError("Solver returned no schedule.")

    print("Solver status:", status)
    if objective is not None:
        print("Objective value:", objective)

    # Render HTML
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    path = render_schedule_html_from_barrister_events(
        schedule,
        title="Barrister Schedule",
        out_path=args.out,
    )

    print("HTML schedule written to:", path)

"""
if __name__ == "__main__":
    main()

# https://ollama.com/download
# ollama --version
# ollama run llama3.1:8b
