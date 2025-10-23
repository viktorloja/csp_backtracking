class CSP:
    # problem structure
    def __init__(self, variables, domains, constraints):
        self.variables = variables  # list like ["X", "Y", "Z"]
        self.domains = domains      # dict: {var: [possible_values]}
        self.constraints = constraints  # dict: { (X, Y): constraint_set }

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
    
def backtrack(assignment, csp):
    if len(assignment) == len(csp.variables):
        return assignment

    for var in csp.variables:
        if var not in assignment:
            for value in csp.domains[var]:
                if csp.is_consistent(var, value, assignment):
                    assignment[var] = value
                    result = backtrack(assignment, csp)
                    if result:
                        return result
                    del assignment[var]
    return None


#cases: list of dicts [{"name": case, "time": time, "senority": senority, "location": location, "duration": duration}, ...]
#barristers: list of dicst [{"name": barrister, "schedule": [dict{start_time, end_time, location}, ...], "senority": senority}, ...]
travel_times = {} #{(start, end): hours, ...}
def define_inputs(cases, barristers):
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
                #add constraint, case1 and case2 cannot have same barrister
                constraints[(name1, name2)] = set()
                constraints[(name2, name1)] = set()
                for barrister1 in domains[name1]:
                    for barrister2 in domains[name2]:
                        if barrister1 != barrister2:
                            constraints[(name1, name2)].add((barrister1, barrister2))
                            constraints[(name2, name1)].add((barrister2, barrister1))

    return variables, domains, constraints

cases = [
    {"name": "CaseA", "time": 10.0, "senority": 2, "location": "Court1", "duration": 1.0},
    {"name": "CaseB", "time": 13.0, "senority": 1, "location": "Court2", "duration": 1.0},
]

barristers = [
    {"name": "Alice", "senority": 2, "schedule": []},
    {"name": "Bob", "senority": 1, "schedule": []},
]

travel_times = {
    ("Court1", "Court2"): 1.0, ("Court2", "Court1"): 1.0
}

variables, domains, constraints = define_inputs(cases, barristers)
print(domains)
print(constraints)
csp = CSP(variables, domains, constraints)
result = backtrack({}, csp)
print(result)

    

            





