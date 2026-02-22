from ortools.sat.python import cp_model
from bisect import bisect_right, bisect_left

UNASSIGNED = "UNASSIGNED"

def setup_model(
    cases,
    barristers,
    travel_times,
    case_costs,
    *,
    lambda_travel=1,
    day_start=0,
    day_end=24 * 60,
    unassigned_penalty=10_000,
    assignment_fixed={},  # dict {case_name: barrister_name}
):
    """
    Builds a CP-SAT model that fully accounts for travel:
      home -> events -> home,
    where events are:
      - mandatory: scheduled blocks
      - optional: cases assigned to that barrister

    Pruning:
      - We only create assign[(case,b)] if the case can fit inside ONE gap between
        consecutive mandatory events for that barrister, using binary search.
      - Fixed assignments create only that assign var (and pin it to 1).

    Objective:
      sum(case_cost * assign) + unassigned_penalty * unassigned + lambda_travel * sum(travel * arc)
    """

    barrister_names = [b["name"] for b in barristers]
    model = cp_model.CpModel()
    
    # ---- Directional travel lookup ----
    def travel(loc_a, loc_b):
        if loc_a == loc_b:
            return 0
        return travel_times.get((loc_a, loc_b), None)

    # ---- Precompute mandatory timeline per barrister: [home_start] + blocks + [home_end] ----
    # Each event: {"start":..., "end":..., "loc":...}
    mandatory_by_b = {}
    mandatory_starts_by_b = {}
    #mandatory_block_starts_by_b = {}  # just block starts (exclude home start/end), for arc pruning
    schedule = {}
    for b in barristers:
        schedule[b["name"]] = []


    #insert all the mandatory blocks
    for b in barristers:
        blocks = b.get("schedule", [])
        bname = b["name"]
        home = b["home"]
        b_start = b.get("day_start", day_start)
        b_end = b.get("day_end", day_end)

        mandatory = [{"start": b_start, "end": b_start, "location": home}]
        for blk in blocks:
            mandatory.append({
                "start": blk["start_time"],
                "end": blk["end_time"],
                "location": blk.get("location", home),
            })
            schedule[bname].append([blk["start_time"], blk["end_time"], blk["location"], "blocked"])
        mandatory.append({"start": b_end, "end": b_end, "location": home})

        mandatory_by_b[bname] = mandatory
        mandatory_starts_by_b[bname] = [e["start"] for e in mandatory]
        #mandatory_block_starts_by_b[bname] = [blk["start_time"] for blk in blocks] #unused

    # ---- Binary-search feasibility: can case be inserted in the surrounding mandatory gap? ----
    # check to see if case can be taken, if it fits in between mandatories
    def case_fits_between_mandatory(case, bname):
        """
        O(log #blocks) using bisect on mandatory starts.
        Returns True if case can fit between two consecutive mandatory events around its start time,
        with travel feasibility on both sides.
        """
        blocks = mandatory_by_b[bname]
        starts = mandatory_starts_by_b[bname]

        c_start = case["time"]
        c_end = c_start + case["duration"]
        c_loc = case["location"]

        # Find the rightmost mandatory event with start <= c_start
        idx = bisect_right(starts, c_start)
      
        if idx == 0 or idx == len(starts):
            return None, None  # outside barrister's working times


        prev_event = blocks[idx-1]
        next_event = blocks[idx]

        # Must lie within the time gap (ignoring travel first)
        if not (prev_event["end"] <= c_start and c_end <= next_event["start"]):
            return None, None

        t_prev = travel(prev_event["location"], c_loc)
        t_next = travel(c_loc, next_event["location"])
        if t_prev is None or t_next is None:
            return None, None

        if prev_event["end"] + t_prev > c_start:
            return None, None
        if c_end + t_next > next_event["start"]:
            return None, None

        return idx-1, idx


    assign = {}      # (case_index, barrister_name) -> BoolVar
    unassigned = {}  # case_index -> BoolVar


    for i, case in enumerate(cases):
        cname = case["name"]
        required_b = assignment_fixed.get(cname, None)

        unassigned[cname] = model.NewBoolVar(f"unassigned__{cname}")

        if required_b is not None:
            # Only create the required assignment var (after sanity checks)
            b_rec = next((bb for bb in barristers if bb["name"] == required_b), None)
            if b_rec is None:
                raise ValueError(f"Fixed assignment refers to unknown barrister: {required_b}")

            if b_rec.get("seniority", 0) < case.get("seniority", 0):
                raise ValueError(f"Fixed assignment {cname}->{required_b} violates seniority.")

            before, after = case_fits_between_mandatory(case, required_b)
            if before is None:
                raise ValueError(f"Fixed assignment {cname}->{required_b} cannot fit around mandatory blocks/home.")

            v = model.NewBoolVar(f"assign__{cname}__to__{required_b}")
            assign[(cname, required_b)] = v
            model.Add(v == 1)
            model.Add(unassigned[cname] == 0)
            continue

        # Non-fixed: create only feasible assign vars
        feasible_vars = []
        for b in barristers:
            bname = b["name"]

            # seniority prune
            if b.get("seniority", 0) < case.get("seniority", 0):
                continue

            # mandatory-gap feasibility prune (binary search)
            before, after = case_fits_between_mandatory(case, bname)
            if before is None:
                continue

            v = model.NewBoolVar(f"assign__{cname}__to__{bname}")
            assign[(cname, bname)] = v
            feasible_vars.append(v)

        # If nobody can take it, force unassigned
        if not feasible_vars:
            model.Add(unassigned[cname] == 1)
        else:
            # exactly one barrister OR unassigned
            model.Add(sum(feasible_vars) + unassigned[cname] == 1)

    cases_length = len(cases)
    case_clashes = set()

    for i in range(cases_length-1):
        for j in range(i+1, cases_length):
            case1 = cases[i]
            case2 = cases[j]
            cname1 = case1["name"]
            cname2 = case2["name"]
            if case1["time"] + case1["duration"] + travel(case1["location"], case2["location"]) > case2["time"]:
                for bname in barrister_names:
                    if (cname1,bname) in assign and (cname2,bname) in assign:
                        model.Add(assign[(cname1,bname)] + assign[(cname2,bname)] <= 1)
                case_clashes.add((case1["name"], case2["name"]))



    # ---- Build full route per barrister: home_start -> events -> home_end ----
    #
    # We create arc variables only for time+travel feasible forward arcs.
    # Additionally, we prune arcs that "skip over" mandatory blocks by time:
    # If there is a mandatory block start between end(u) and start(v), then u->v can't be used
    # because that block must appear in the route. (Safe prune.)
    all_travel_arc_terms = []

    def skips_mandatory_block(bname, u_end, v_start):
            """
            Safe prune: if any mandatory block start is in [u_end, v_start],
            then an arc u->v would necessarily skip a mandatory node.
            """
            block_starts = mandatory_starts_by_b[bname]
            left = bisect_left(block_starts, u_end)
            right = bisect_right(block_starts, v_start)
            #left = bisect_right(block_starts, u_end)
            #right = bisect_left(block_starts, v_start)
            return left != right

    for b in barristers:
        bname = b["name"]
        mandatory = mandatory_by_b[bname]

        mandatory_nums = len(mandatory)-1

        present = [1]*(mandatory_nums+1)
        viable_cases = {}


        offset = 0
        for i, case in enumerate(cases):
            cname = case["name"]
            if (cname, bname) not in assign: # case not feasible for barrister
                continue
            present.append(assign[(cname, bname)])
            offset += 1
            viable_cases[mandatory_nums+offset] = case

        incoming = [[] for _ in range(mandatory_nums+offset+1)]
        outgoing = [[] for _ in range(mandatory_nums+offset+1)]

        # travel arcs between each mandatory event to the next
        for j in range(mandatory_nums):
            x = model.NewBoolVar(f"arc__{bname}__{j}_to_{j+1}")
            outgoing[j].append(x)
            incoming[j+1].append(x)

            man1_loc = mandatory[j]["location"]
            man2_loc = mandatory[j+1]["location"]
            
            tcost = travel(man1_loc, man2_loc)
            all_travel_arc_terms.append(tcost * x)

        # travel arcs for each event and its bordering mandatory events
        for j in range(mandatory_nums+1, mandatory_nums+offset+1):
            case = viable_cases[j]
            before, after = case_fits_between_mandatory(case, bname)

            x = model.NewBoolVar(f"arc__{bname}__{before}_to_{j}")
            outgoing[before].append(x)
            incoming[j].append(x)

            before_loc = mandatory[before]["location"]
            tcost = travel(before_loc, case["location"])

            all_travel_arc_terms.append(tcost * x)

            x = model.NewBoolVar(f"arc__{bname}__{j}_to_{after}")
            outgoing[j].append(x)
            incoming[after].append(x)

            after_loc = mandatory[after]["location"]
            tcost = travel(case["location"], after_loc)

            all_travel_arc_terms.append(tcost * x)

        # travel arcs for each event and the following event (if no mandatories are skipped)
        for j in range(mandatory_nums+1, mandatory_nums+offset):
            case1 = viable_cases[j]
            for k in range(j+1, mandatory_nums+offset+1):
                case2 = viable_cases[k]
                if (case1["name"], case2["name"]) in case_clashes:
                    continue
                if not skips_mandatory_block(bname, case1["time"]+case1["duration"], case2["time"]):
                    x = model.NewBoolVar(f"arc__{bname}__{j}_to_{k}")
                    outgoing[j].append(x)
                    incoming[k].append(x)

                    tcost = travel(case1["location"], case2["location"])

                    all_travel_arc_terms.append(tcost * x)


        # Ensure start has exactly 1 outgoing, end has exactly 1 incoming
        model.Add(sum(outgoing[0]) == 1)
        model.Add(sum(incoming[0]) == 0)
        model.Add(sum(incoming[mandatory_nums]) == 1)
        model.Add(sum(outgoing[mandatory_nums]) == 0)

        # For each internal event e:
        #   sum_in(e)  == present(e)
        #   sum_out(e) == present(e)
        for e in range(1, mandatory_nums+offset+1):
            if e != mandatory_nums:
                p = present[e]

                if isinstance(p, int):
                    if p == 1:
                        model.Add(sum(incoming[e]) == 1)
                        model.Add(sum(outgoing[e]) == 1)
                    else:  # p == 0
                        model.Add(sum(incoming[e]) == 0)
                        model.Add(sum(outgoing[e]) == 0)
                else:
                    # p is a BoolVar
                    model.Add(sum(incoming[e]) == p)
                    model.Add(sum(outgoing[e]) == p)

        # ensure a case is in the timeline if assigned to barrister, otherwise not if not assigned to barrister
        # also ensure each case has 1 outgoing and 1 incoming, this prevents two cases overlapping since arcs are valid and this would force 2 incoming / 2 outgoing on neighbouring cases

    # ---- Case cost + unassigned penalty terms ----
    cost_terms = []
    for i, case in enumerate(cases):
        cname = case["name"]
        cost_terms.append(unassigned_penalty * unassigned[cname])
        for bname in barrister_names:
            if (cname, bname) in assign:
                cost = case_costs.get((cname, bname), 999999)
                cost_terms.append(cost * assign[(cname, bname)])

    # ---- Objective: case cost + lambda * travel ----
    model.Minimize(sum(cost_terms) + lambda_travel * sum(all_travel_arc_terms))

    return model, assign, unassigned, cases, schedule


def solve_model(model, assign, unassigned, cases, schedule, *, max_time_seconds=10):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    status = solver.Solve(model)

    cases_by_name = {}
    for case in cases:
        cases_by_name[case["name"]] = case

    result = {
        "status": solver.StatusName(status),
        "objective": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "schedule": None,
        "assignment": None,
        "unassigned_cases": None,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return result

    assignment = {}
    unassigned_cases = []

    for cname, var in unassigned.items():
        if solver.Value(var) == 1:
            unassigned_cases.append(cname)

    for (cname, bname), var in assign.items():
        if solver.Value(var) == 1:
            assert solver.Value(unassigned[cname]) == 0 # ensure our solver worked correctly
            case = cases_by_name[cname]
            assignment[cname] = bname
            schedule[bname].append([case["time"], case["time"]+case["duration"], case["location"], case["name"]])

    for bschedule in schedule.values():
        bschedule.sort()
    
    result["schedule"] = schedule
    result["assignment"] = assignment
    result["unassigned_cases"] = unassigned_cases
    return result