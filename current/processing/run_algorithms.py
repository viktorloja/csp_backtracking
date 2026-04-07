from algorithms.ortoolssolver3 import *
from algorithms.backtrack_optimized import *
from algorithms.greedy_most_constrained import greedy
from algorithms.backtrack_naive import *
from algorithms.local_search import local_search
import tracemalloc
import time

# prioritising most experienced barristers
def calculate_costs_optimal(cases, barristers):
    case_costs = {}
    for case in cases:
        for barrister in barristers:
            cost = 600
            if case["type"] in barrister["expertise"]:
                cost -= 200
            cost -= min(200, barrister.get("experience", 5)*10)
            cost -= 200*barrister["winrate"]
            case_costs[(case["name"], barrister["name"])] = cost

    return case_costs

# prioritising assigning inexperienced barristers for training on insevere cases
def calculate_costs_balanced(cases, barristers):
    case_costs = {}
    for case in cases:
        for barrister in barristers:
            cost = 700
            if case["type"] in barrister["expertise"]:
                cost -= 200
            if not case["severe"] and barrister["experience"] < 3: # case not too severe so can be used for training
                cost -= 300 # heavily prioritised inexperienced barristers to give training opportunities
            else:
                cost -= min(200, barrister["experience"]*10)
            cost -= 200*barrister["winrate"]
            case_costs[(case["name"], barrister["name"])] = cost

    return case_costs
                

def evaluate(barristers, travel_times, schedule):

    barrister_info = {}
    for barrister in barristers:
        barrister_info[barrister["name"]] = barrister["home"]

    score = {}
        
    #locations = {}
    ####
    """
    for barrister in barristers:
        name = barrister["name"]
        scores[name] = 0
        locations[name] = barrister["home"]

    for case in cases:
        casename = case["name"]
        if casename in best_solution:
            barrister = best_solution[casename] 
            scores[barrister] += (case["duration"] + travel_times[(locations[barrister], case["location"])])
            locations[barrister] = case["location"]
    """
    ####
    for barrister in schedule.keys():
        score[barrister] = 0
        bschedule = schedule[barrister]
        if bschedule:
            score[barrister] += travel_times[(barrister_info[barrister], bschedule[0][2])]
            score[barrister] += travel_times[(bschedule[-1][2], barrister_info[barrister])]

            for i in range(len(schedule[barrister])-1):
                score[barrister] += travel_times[(bschedule[i][2], bschedule[i+1][2])]
            

    total_1= 0
    total_2 = 0
    total_sqr = 0
    n = 0

    for score1 in score.values():
        n += 1
        total_1 += score1
        total_sqr += (score1**2)
        for score2 in score.values():
            total_2 += abs(score1-score2)
    
    gini = total_1 / (2 * n * total_2)
    jain = total_1**2 / (n * total_sqr)

    return gini, jain


def generate_schedule(cases, barristers, travel_times,
                assignment_fixed={},
                method="ortools",
                training=False,
                **kwargs):

    """
    Solve the case assignment problem using the chosen method.
    
    method options:
        - "ortools"
        - "backtrack_optimized"
        - "backtrack_naive"
        - "greedy"
    """
    
    output = {}
    cases_sorted = sorted(cases, key=lambda c: c["time"])
    if training:
        case_costs = calculate_costs_balanced(cases_sorted, barristers)
    else:
        case_costs = calculate_costs_optimal(cases_sorted, barristers)


    if method == "ortools":

        model, assign, unassigned, cases_sorted, schedule = setup_model(
            cases_sorted,
            barristers,
            travel_times,
            case_costs,
            assignment_fixed=assignment_fixed,
        )

        tracemalloc.start()
        start_time = time.time()

        result = solve_model(model, assign, unassigned, cases_sorted, schedule)

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        output["result"] = result["assignment"]
        output["schedule"] = result["schedule"]
        output["score"] = result["objective"]
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6
        
        bnames = []
        #print(output)
        #output["fairness"] = evaluate(barristers, travel_times, result["schedule"])

    elif method == "backtrack_optimized":
        
        domains, constraints, timelines, timelines_starts = define_inputs(cases_sorted, barristers, travel_times)
    
        tracemalloc.start()
        start_time = time.time()

        solution, cost, schedules = branch_and_bound_optimized(
            cases,
            timelines,
            timelines_starts,
            travel_times,
            case_costs,
            domains,
            constraints,
        )


        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        output["result"] = solution
        output["schedule"] = schedules
        output["score"] = cost
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6
        #output["fairness"] = evaluate(cases_sorted, barristers, best_sol())

    elif method == "backtrack_naive":

        domains, constraints, timelines, timelines_starts = define_inputs(cases_sorted, barristers, travel_times)
    
        tracemalloc.start()
        start_time = time.time()

        solution, cost, schedules = branch_and_bound_naive(
            cases,
            timelines,
            timelines_starts,
            travel_times,
            case_costs,
            domains,
            constraints,
        )


        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        output["result"] = solution
        output["schedule"] = schedules
        output["score"] = cost
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6

    elif method == "local_search":

        tracemalloc.start()
        start_time = time.time()

        solution, schedules, starts, cost = greedy(
            cases,
            barristers,
            travel_times,
            case_costs,
            assignment_fixed = assignment_fixed
        )

        solution, schedules, cost = local_search(
            barristers,
            cases,
            solution,
            schedules,
            starts,
            case_costs,
            travel_times,
            cost
        )

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        output["result"] = solution
        output["schedule"] = schedules
        output["score"] = cost
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6

    elif method == "greedy":

        tracemalloc.start()
        start_time = time.time()

        solution, schedules, starts, cost = greedy(
            cases,
            barristers,
            travel_times,
            case_costs,
            assignment_fixed = assignment_fixed
        )

        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        output["result"] = solution
        output["schedule"] = schedules
        output["score"] = cost
        output["runtime"] = end_time - start_time
        output["memory"] = peak / 10**6


    else:
        raise ValueError(f"Unknown method: {method}")

    return output
