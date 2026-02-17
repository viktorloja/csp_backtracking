from math import inf

class CSP:
    # problem structure
    def __init__(self, variables, domains, constraints, costs):
        self.variables = variables  # list like ["X", "Y", "Z"]
        self.domains = domains      # dict: {var: [possible_values]}
        self.constraints = constraints  # dict: { (X, Y): constraint_set }
        self.neighbours = {v: set() for v in variables}
        for (x, y) in constraints:
            self.neighbours[x].add(y)
        self.costs = costs # dict of dicts : { X: {var: cost } }


def heuristic_lower_bound(remaining_cases, csp):
  
    bound = 0
    for case in remaining_cases:
        current = 1000
        for barrister in csp.domains[case]:
            current = min(csp.costs[(case, barrister)], current)
        bound += current
    return bound


def forward_check(csp, case, barrister, assignment):
    removed = set()
    nones = set()
    cost = 0
    for (case1, case2) in csp.constraints:
        if case1 == case and case2 not in assignment:
            if barrister in csp.domains[case2]:
                csp.domains[case2].remove(barrister)
                removed.add(case2)
            if not csp.domains[case2]:  # dead-end
                cost += 1000
                nones.add(case2)
    return nones, cost, removed


best_solution = None
best_cost = inf
step_counter = 0

def branch_and_bound(assignment, remaining_cases, current_cost, csp):
    
    global best_solution, best_cost, step_counter

    step_counter += 1

    # Base case: all cases assigned
    if not remaining_cases:
        if current_cost < best_cost:
            best_cost = current_cost
            best_solution = assignment.copy()
            print(f"New best solution found: {assignment}, cost={best_cost}")
        return

    # Compute lower bound for this partial assignment
    bound = current_cost + heuristic_lower_bound(remaining_cases, csp)
    if bound >= best_cost:
        # Prune this branch (no better solution possible)
        print(f"Pruned branch: cost={current_cost}, bound={bound}, best={best_cost}")
        return

    # Choose next case to assign, MRV variable
    case = min(remaining_cases, key=lambda v: len(csp.domains[v]))


    # Try all feasible barristers
    for barrister in csp.domains[case]:
        new_cost = current_cost + csp.costs[(case, barrister)]
        assignment[case] = barrister
        nones, cost, removed = forward_check(csp, case, barrister, assignment)
        branch_and_bound(assignment, remaining_cases - set([case]) - nones, new_cost+cost, csp)
            
        # Restore domains
        for y in removed:
            csp.domains[y].append(barrister)

        del assignment[case]  # backtrack

#cases: list of dicts [{"name": case, "time": time, "seniority": seniority, "location": location, "duration": duration}, ...]
#barristers: list of dicst [{"name": barrister, "schedule": [dict{start_time, end_time, location}, ...], "seniority": seniority, "home": home_location}, ...]
#travel_times: {(start, end): hours, ...}
def define_inputs(cases, barristers, travel_times):
    n = len(cases)

    variables = []
    domains = {}
    
    for case in cases:
        name = case["name"]
        variables.append(name)
        domains[name] = []
        for barrister in barristers:
            if barrister["seniority"] >= case["seniority"]:
                case_time = case["time"]
                case_duration = case["duration"]
                case_location = case["location"]
                barrister_blocks = barrister["schedule"] #list of dicts
                m = len(barrister_blocks)
                if m == 0:
                    domains[name].append(barrister["name"])
                else:
                    for i in range(m+1):
                        if i == 0: #check to see if they can do the case before their first block
                            block = barrister_blocks[i]
                            if (block["start_time"] - travel_times[(case_location, block["location"])]) >= case_time + case_duration:
                                domains[name].append(barrister["name"])
                                break
                        elif i == m: #check to see if they can do the case after their last block
                            block = barrister_blocks[-1]
                            if (block["end_time"] + travel_times[(block["location"], case_location)]) <= case_time:
                                domains[name].append(barrister["name"])
                                break
                        else: #check to see if they can do the case between blocks
                            block_after = barrister_blocks[i]
                            block_before = barrister_blocks[i-1]
                            if (block_before["end_time"] + travel_times[(block_before["location"], case_location)]) <= case_time and (block_after["start_time"] - travel_times[(case_location, block_after["location"])]) >= case_time + case_duration:
                                domains[name].append(barrister["name"])
                                break



    constraints = {}

    for i in range(n-1):
        for j in range(i+1, n):
            case1 = cases[i]
            case2 = cases[j]
            name1 = case1["name"]
            name2 = case2["name"]
            if (case2["time"] - case1["time"]) < (travel_times[(case1["location"], case2["location"])] + case1["duration"]): #if cases are too close together considering travel and case time
                # add constraint, case1 and case2 cannot have same barrister
                constraints[(name1, name2)] = set()
                constraints[(name2, name1)] = set()
                for barrister1 in domains[name1]:
                    for barrister2 in domains[name2]:
                        if barrister1 != barrister2:
                            constraints[(name1, name2)].add((barrister1, barrister2))
                            constraints[(name2, name1)].add((barrister2, barrister1))

    return variables, domains, constraints

#optimization (cost) 
#categories of cases
#experience
#winrate of cases
#fake barrister profiles - NLP to extract, consult chambers with fake profiles, generate fake profiles/history
#public info fenners chambers
#suggest new experience
#design barrister profile, add to data struct
#visualise schedule / simple UI - library to show schedule table
#metrics to evaluate quality, scoring mechanism
#ortools (library)
#evaluation - human participants? - ethics committee
#machine learning for scoring?


#completed: OR-tools
#parent function for OR-tools / backtrack
#evaluation function, gini coefficient
def best_sol():
    print(best_solution)
    return best_solution


#create proper test corpus - sufficiently large and conflicted
#profiles for (criminal) cases and (mix of crime & civil) barristers, markdown files
#in-depth barrister profiles - number of cases, types, years, winrate
#list of barristers and their cases, then map this to a data structure
#cases: fees, charges (type - robbery, petty theft, etc.), punishment (severity), person being charged etc.

#generate model files for now

#scenarios: too many cases, partial assignments
#           improper experience
#           


#two different schedules? an optimized one, and one for getting barristers more experience
#is a case 'critical' or not?
#case files, possible prison sentence - critical or not
#process a paragraph of text, NLP library?
#generate case files
#evaluate against human judgement
#process PDFs - extract text
#barrister preferences / how they work better
#evaluate against an LLM doing scheduling


