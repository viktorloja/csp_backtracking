import argparse
from pathlib import Path
from tests.generate_test_cases import generate_test_case
from processing.run_algorithms import generate_schedule
from output.html_output import render_schedule_html_from_barrister_events
from output.metrics_graph import plot_graphs


def main():
    parser = argparse.ArgumentParser(
        description="Barrister scheduling pipeline"
    )

    parser.add_argument(
        "--barristers",
        default=[30],
        help="Number of barristers",
    )

    parser.add_argument(
        "--load",
        default=[0.5],
        help="The desired ratio of total case minutes / available barrister minutes, e.g. 0.4 = easy, 0.7 = moderate, 0.9 = hard, 1.1 = very hard",
    )

    parser.add_argument(
        "--locations",
        default=[7],
        help="Number of locations",
    )

    parser.add_argument(
        "--constraint",
        default=[0.3],
        help="Level of constrainedness, 0.0 is least, 1.0 is most",
    )

    parser.add_argument(
        "--phase",
        default=["phase_transition"],
        help="Phase of difficulty, e.g. easy, phase_transition, hard",
    )

    parser.add_argument(
        "--output",
        default="data/outputs",
        help="Output directory",
    )

    parser.add_argument(
        "--training",
        default=[False],
        help="Enable training mode to prioritize lower experience barristers",
    )

    args = parser.parse_args()
    length = len(args.barristers)
    #solvers = ["ortools", "backtrack_optimized", "backtrack_naive", "greedy"]
    #solvers = ["ortools", "local_search", "greedy"]
    solvers = ["ortools", "local_search", "greedy", "backtrack_optimized", "backtrack_naive"]
    solvers = ["exhaustive_greedy", "local_search"]

    experiments = []

    plots_dir = Path(args.output + "/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    schedules_dir = Path(args.output + "/schedules")
    schedules_dir.mkdir(parents=True, exist_ok=True)

    for i in range(length):

        results = {}
        barristers, cases, travel_times = generate_test_case(args.barristers[i], args.locations[i], args.constraint[i], args.load[i], args.phase[i])

        for solver in solvers:
            print("Running solver: "+solver)

            result = generate_schedule(
                method=solver,
                barristers=barristers,
                cases=cases,
                travel_times=travel_times,
                training=args.training[i],
            )
            #print(result)

            schedule = result["schedule"]

            if not schedule:
                raise RuntimeError(solver+" solver returned no schedule.")

            # Render HTML
            
            file_name = "schedule-"+str(i)+"-"+solver+".html"
            file_path = schedules_dir / file_name

            html_path = render_schedule_html_from_barrister_events(
                schedule,
                title="Barrister Schedule",
                out_path=file_path,
            )

            #print("HTML "+solver+"-schedule written to: "+html_path)
            
            results[solver] = result

        experiments.append(results)
        file_name = "plot-"+str(i)+".png"
        file_path = plots_dir / file_name
        plot_graphs(results, file_path)
            

    for experiment in experiments:
        for key in experiment.keys():
            print(key)
            print(experiment[key]["score"])
            #cases = []
            #for case in experiment[key]["result"].keys():
            #    cases.append((case, experiment[key]["result"][case]))

            #cases.sort()
            #print(cases)



    #plot_graph(experiments, args.output)

if __name__ == "__main__":
    main()