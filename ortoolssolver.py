from ortools.sat.python import cp_model

def solve_cases_min_travel(cases, barristers, travel_times, assignment_fixed=None, max_time_seconds=30):
    # ----- Preprocess & indexing -----
    cases_sorted = sorted(cases, key=lambda c: c["time"])
    n = len(cases_sorted)

    barrister_names = [b["name"] for b in barristers]

    model = cp_model.CpModel()

    # ----- Feasible assign variables only -----
    assign = {}
    for i, case in enumerate(cases_sorted):
        cstart = case["time"]
        cend = cstart + case["duration"]
        for b in barristers:
            # seniority filter
            if b["seniority"] < case.get("seniority", 0):
                continue
            # check schedule feasibility
            feasible = True
            for blk in b.get("schedule", []):
                blk_s, blk_e = blk["start_time"], blk["end_time"]
                loc_blk = blk.get("location")
                t_to = travel_times.get((loc_blk, case["location"]))
                t_from = travel_times.get((case["location"], loc_blk))
                if cend + t_from > blk_s or blk_e + t_to > cstart:
                    feasible = False
                    break
            if feasible:
                assign[(i, b["name"])] = model.NewBoolVar(f"assign_c{i}_{case['name']}__b_{b['name']}")

    # ----- Each case assigned exactly one feasible barrister -----
    for i in range(n):
        model.Add(sum(assign[(i,b)] for (ii,b) in assign if ii==i) == 1)

    # ----- Partial fixed assignments -----
    if assignment_fixed:
        for cname, bname in assignment_fixed.items():
            i = next(idx for idx,c in enumerate(cases_sorted) if c["name"]==cname)
            if (i, bname) in assign:
                model.Add(assign[(i,bname)] == 1)
            for key in list(assign):
                if key[0]==i and key[1]!=bname:
                    model.Add(assign[key] == 0)

    # ----- No-overlap / travel constraints -----
    for i in range(n):
        ci = cases_sorted[i]
        si, ei, loc_i = ci["time"], ci["time"]+ci["duration"], ci["location"]
        for j in range(i+1, n):
            cj = cases_sorted[j]
            sj, ej, loc_j = cj["time"], cj["time"]+cj["duration"], cj["location"]

            # compute travel feasibility
            travel_ij = travel_times.get((loc_i, loc_j), None)
            travel_ji = travel_times.get((loc_j, loc_i), None)
            feasible_ij = travel_ij is not None and sj >= ei + travel_ij
            feasible_ji = travel_ji is not None and si >= ej + travel_ji

            # if overlap or infeasible travel, forbid same barrister
            if not (feasible_ij or feasible_ji) or not (ej <= si or ei <= sj):
                for b in barrister_names:
                    if (i,b) in assign and (j,b) in assign:
                        model.Add(assign[(i,b)] + assign[(j,b)] <= 1)

    # ----- Successor (next) variables for travel minimization -----
    next_var = {}
    for b in barrister_names:
        for i in range(n):
            for j in range(i+1, n):
                if (i,b) in assign and (j,b) in assign:
                    if cases_sorted[j]["time"] >= cases_sorted[i]["time"] + cases_sorted[i]["duration"]:
                        next_var[(b,i,j)] = model.NewBoolVar(f"next__b_{b}__c{i}_to_c{j}")
                        model.Add(next_var[(b,i,j)] <= assign[(i,b)])
                        model.Add(next_var[(b,i,j)] <= assign[(j,b)])
                        for k in range(i+1,j):
                            if (k,b) in assign:
                                model.Add(next_var[(b,i,j)] + assign[(k,b)] <= 1)

    # ----- Link next variables to assignments (forward) -----
    for b in barrister_names:
        for i in range(n):
            later = [j for j in range(i+1,n) if (b,i,j) in next_var]
            if not later:
                continue
            y = model.NewBoolVar(f"hasLater__b_{b}__c{i}")
            #force y to equal 1 if later case exists, 0 otherwise
            model.Add(sum(next_var[(b,i,j)] for j in later) >= y) 
            model.Add(sum(next_var[(b,i,j)] for j in later) <= len(later)*y) 
            # z = assign(i,b) AND y
            z = model.NewBoolVar(f"z_forward__b_{b}__c{i}")
            #force z to equal 1 if there is a case after i, 0 otherwise
            model.Add(z <= assign[(i,b)])
            model.Add(z <= y)
            model.Add(z >= assign[(i,b)] + y - 1)
            model.Add(sum(next_var[(b,i,j)] for j in later) == z)
            #ensure only one forward arc per case

    # ----- Objective: minimize total travel along consecutive edges -----
    travel_terms = []
    for (b,i,j), var in next_var.items():
        loc_i = cases_sorted[i]["location"]
        loc_j = cases_sorted[j]["location"]
        travel = travel_times.get((loc_i, loc_j), 0)
        travel_terms.append(travel*var)
    model.Minimize(sum(travel_terms))

    # ----- Solve -----
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    status = solver.Solve(model)

    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        solution = {}
        for (i,b), var in assign.items():
            if solver.Value(var):
                solution[cases_sorted[i]["name"]] = b
        return {
            "status": solver.StatusName(status),
            "assignment": solution,
            "objective_travel": solver.ObjectiveValue()
        }
    else:
        return {"status": solver.StatusName(status), "assignment": None}
    
cases = [
    {"name": "A", "time": 10*60, "duration": 60, "location": "Loc1", "seniority": 1},
    {"name": "B", "time": 11*60+30, "duration": 60, "location": "Loc1", "seniority": 1},
    {"name": "C", "time": 16*60, "duration": 60, "location": "Loc2", "seniority": 1},
    {"name": "D", "time": 17*60+30, "duration": 60, "location": "Loc2", "seniority": 1},
]

barristers = [
    {"name": "Alice", "seniority": 2, "schedule": [], "home": "Loc1"},
    {"name": "Bob", "seniority": 2, "schedule": [], "home": "Loc2"},
]

travel_times = {
    ("Loc1","Loc1"):0, ("Loc2","Loc2"):0,
    ("Loc1","Loc2"):120, ("Loc2","Loc1"):120,
}

res = solve_cases_min_travel(cases, barristers, travel_times)
print(res)