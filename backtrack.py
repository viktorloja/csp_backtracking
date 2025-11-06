class CSP:
    # problem structure
    def __init__(self, variables, domains, constraints):
        self.variables = variables  # list like ["X", "Y", "Z"]
        self.domains = domains      # dict: {var: [possible_values]}
        self.constraints = constraints  # dict: { (X, Y): constraint_set }
        self.neighbours = {v: set() for v in variables}
        for (x, y) in constraints:
            self.neighbours[x].add(y)

    def is_consistent(self, var, value, assignment):
        # Check that assigning var=value doesn’t violate any constraints
        for (x, y), allowed_pairs in self.constraints.items():
            if x == var and y in assignment:
                if (value, assignment[y]) not in allowed_pairs:
                    return False
            if y == var and x in assignment:
                if (assignment[x], value) not in allowed_pairs:
                    return False
        return True
    
    def is_consistent(self, var, value, assignment):
        for neighbour in self.neighbours[var]:
            if neighbour in assignment:
                allowed = self.constraints.get((var, neighbour))
                if allowed and (value, assignment[neighbour]) not in allowed:
                    return False
        return True

def forward_check(csp, var, value, assignment):
    removed = {}
    for (x, y), allowed in csp.constraints.items():
        if x == var and y not in assignment:
            removed[y] = []
            if value in csp.domains[y]:
                csp.domains[y].remove(value)
                removed[y].append(value)
            if not csp.domains[y]:  # dead-end
                return False, removed
    return True, removed

def backtrack(assignment, csp):
    if len(assignment) == len(csp.variables):
        return assignment
    
    # MRV variable
    unassigned = [v for v in csp.variables if v not in assignment]
    var = min(unassigned, key=lambda v: len(csp.domains[v]))

    for value in csp.domains[var]:
        if csp.is_consistent(var, value, assignment):
            assignment[var] = value

            ok, removed = forward_check(csp, var, value, assignment)
            if ok:
                result = backtrack(assignment, csp)
                if result:
                    return result
                
            # Restore domains
            for y, vals in removed.items():
                csp.domains[y].extend(vals)

            del assignment[var]
                 
    return None
            


#cases: list of dicts [{"name": case, "time": time, "senority": senority, "location": location, "duration": duration}, ...]
#barristers: list of dicst [{"name": barrister, "schedule": [dict{start_time, end_time, location}, ...], "senority": senority}, ...]
#travel_times: {(start, end): hours, ...}
def define_inputs(cases, barristers, travel_times):
    n = len(cases)
    cases.sort(key=lambda x: x["time"])

    variables = []
    domains = {}
    
    for case in cases:
        name = case["name"]
        variables.append(name)
        domains[name] = []
        for barrister in barristers:
            if barrister["senority"] >= case["senority"]:
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

#categories of cases
#experience
#winrate of cases
#fake barrister profiles
#public info fenners chambers
#suggest new experience
#design barrister profile, add to data struct
#visualise schedule / simple UI - library to show schedule table
#metrics to evaluate quality, scoring mechanism