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

    num_cases = len(cases_sorted)
    case_name_to_index = {c["name"]: i for i, c in enumerate(cases_sorted)}
    barrister_names = [b["name"] for b in barristers]
    blocks = b.get("schedule", [])

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
    mandatory_block_starts_by_b = {}  # just block starts (exclude home start/end), for arc pruning
    schedule = {}
    for b in barristers:
        schedule[b["name"]] = []


    #insert all the mandatory blocks
    for b in barristers:
        bname = b["name"]
        home = b["home"]

        mandatory = [{"start": day_start, "end": day_start, "loc": home}]
        for blk in blocks:
            mandatory.append({
                "start": blk["start_time"],
                "end": blk["end_time"],
                "loc": blk.get("location", home),
            })
            schedule[bname].append([blk["start_time"], blk["end_time"], blk["location"], "blocked"])
        mandatory.append({"start": day_end, "end": day_end, "loc": home})

        mandatory_by_b[bname] = mandatory
        mandatory_starts_by_b[bname] = [e["start"] for e in mandatory]
        mandatory_block_starts_by_b[bname] = [blk["start_time"] for blk in blocks] #unused

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
        idx = bisect_right(starts, c_start) - 1
        if idx < 0:
            idx = 0
        if idx >= len(blocks) - 1:
            return False  # beyond barrister end time

        prev_event = blocks[idx]
        next_event = blocks[idx + 1]

        # Must lie within the time gap (ignoring travel first)
        if not (prev_event["end"] <= c_start and c_end <= next_event["start"]):
            return False

        t_prev = travel(prev_event["loc"], c_loc)
        t_next = travel(c_loc, next_event["loc"])
        if t_prev is None or t_next is None:
            return False

        if prev_event["end"] + t_prev > c_start:
            return False
        if c_end + t_next > next_event["start"]:
            return False

        return True


    assign = {}      # (case_index, barrister_name) -> BoolVar
    unassigned = {}  # case_index -> BoolVar


    for i, case in enumerate(cases):
        cname = case["name"]
        required_b = assignment_fixed.get(cname, None)

        unassigned[i] = model.NewBoolVar(f"unassigned__{cname}")

        if required_b is not None:
            # Only create the required assignment var (after sanity checks)
            b_rec = next((bb for bb in barristers if bb["name"] == required_b), None)
            if b_rec is None:
                raise ValueError(f"Fixed assignment refers to unknown barrister: {required_b}")

            if b_rec.get("seniority", 0) < case.get("seniority", 0):
                raise ValueError(f"Fixed assignment {cname}->{required_b} violates seniority.")

            if not case_fits_between_mandatory(case, required_b):
                raise ValueError(f"Fixed assignment {cname}->{required_b} cannot fit around mandatory blocks/home.")

            v = model.NewBoolVar(f"assign__{cname}__to__{required_b}")
            assign[(i, required_b)] = v
            model.Add(v == 1)
            model.Add(unassigned[i] == 0)
            continue

        # Non-fixed: create only feasible assign vars
        feasible_vars = []
        for b in barristers:
            bname = b["name"]

            # seniority prune
            if b.get("seniority", 0) < case.get("seniority", 0):
                continue

            # mandatory-gap feasibility prune (binary search)
            if not case_fits_between_mandatory(case, bname):
                continue

            v = model.NewBoolVar(f"assign__{cname}__to__{bname}")
            assign[(i, bname)] = v
            feasible_vars.append(v)

        # If nobody can take it, force unassigned
        if not feasible_vars:
            model.Add(unassigned[i] == 1)
        else:
            # exactly one barrister OR unassigned
            model.Add(sum(feasible_vars) + unassigned[i] == 1)

    # ---- Build full route per barrister: home_start -> events -> home_end ----
    #
    # We create arc variables only for time+travel feasible forward arcs.
    # Additionally, we prune arcs that "skip over" mandatory blocks by time:
    # If there is a mandatory block start between end(u) and start(v), then u->v can't be used
    # because that block must appear in the route. (Safe prune.)
    all_travel_arc_terms = []

    for b in barristers:
        bname = b["name"]
        home_loc = b["home"]

        # Build event lists for this barrister
        # Index 0 = S (home start), last = T (home end)
        event_start = []
        event_end = []
        event_loc = []
        present = []  # 1 for mandatory, BoolVar for optional (case assigned), 0 for absent

        # S
        event_start.append(day_start)
        event_end.append(day_start)
        event_loc.append(home_loc)
        present.append(1)

        # Mandatory blocks
        for blk in blocks:
            event_start.append(blk["start_time"])
            event_end.append(blk["end_time"])
            event_loc.append(blk.get("location", home_loc))
            present.append(1)

        # Optional case events: only include if assign var exists for (i,bname)
        # (This is a big model-size win.)

        for i, case in enumerate(cases):
            if (i, bname) not in assign: # case not feasible for barrister
                continue
            event_start.append(case["time"])
            event_end.append(case["time"] + case["duration"])
            event_loc.append(case["location"])
            present.append(assign[(i, bname)])
            #case_event_case_index.append(i)
        # all optinal cases are given a 'present' value equal to if they're assigned to this barrister

        # T
        event_start.append(day_end)
        event_end.append(day_end)
        event_loc.append(home_loc)
        present.append(1)

        T_idx = len(event_start) - 1
        num_events = len(event_start)

        # Block-starts list for safe arc pruning
        block_starts = [blk["start_time"] for blk in blocks]  # sorted

        # prune impossible arcs/ordering (e.g. case A -> case B but theres a mandatory in between)
        def skips_mandatory_block(u_end, v_start):
            """
            Safe prune: if any mandatory block start is in [u_end, v_start],
            then an arc u->v would necessarily skip a mandatory node.
            """
            if not block_starts:
                return False
           #left = bisect_left(block_starts, u_end)
           #right = bisect_right(block_starts, v_start)
            left = bisect_right(block_starts, u_end)
            right = bisect_left(block_starts, v_start)
            return left < right

        # Create arc vars for feasible forward arcs
        arc = {}
        incoming = [[] for _ in range(num_events)]
        outgoing = [[] for _ in range(num_events)]

        for u in range(num_events):
            if u == T_idx:
                continue
            for v in range(num_events):
                if v == 0:
                    continue
                if v == u:
                    continue

                # forward by time window
                if event_start[v] < event_end[u]:
                    continue

                tcost = travel(event_loc[u], event_loc[v])
                if tcost is None:
                    continue
                if event_end[u] + tcost > event_start[v]:
                    continue

                # safe prune: don't allow skipping mandatory block times
                if skips_mandatory_block(event_end[u], event_start[v]):
                    # Exception: allow arcs that go *into* the first block when u is S and v is that block.
                    # (This is already fine because then u_end is day_start, v_start is block_start; it doesn't skip.)
                    continue

                x = model.NewBoolVar(f"arc__{bname}__{u}_to_{v}")
                arc[(u, v)] = x
                outgoing[u].append(x)
                incoming[v].append(x)
                all_travel_arc_terms.append(tcost * x)
                # create ordering of all events that can follow eachother

        # Ensure S has exactly 1 outgoing, T has exactly 1 incoming
        model.Add(sum(outgoing[0]) == 1)
        model.Add(sum(incoming[0]) == 0)
        model.Add(sum(incoming[T_idx]) == 1)
        model.Add(sum(outgoing[T_idx]) == 0)

        # For each internal event e:
        #   sum_in(e)  == present(e)
        #   sum_out(e) == present(e)
        for e in range(1, T_idx):
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
        cost_terms.append(unassigned_penalty * unassigned[i])
        for bname in barrister_names:
            if (i, bname) in assign:
                cost = case_costs.get((cname, bname), 999999)
                cost_terms.append(cost * assign[(i, bname)])

    # ---- Objective: case cost + lambda * travel ----
    model.Minimize(sum(cost_terms) + lambda_travel * sum(all_travel_arc_terms))

    return model, assign, unassigned, cases, schedule


def solve_model(model, assign, unassigned, cases_sorted, schedule, *, max_time_seconds=10):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    status = solver.Solve(model)

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

    n = len(cases_sorted)

    for i in range(n):
        if solver.Value(unassigned[i]) == 1:
            unassigned_cases.append(case["name"])

    for (case_i, bname), var in assign.items():
        if solver.Value(var) == 1:
            assert solver.Value(unassigned[case_i]) == 0 # ensure our solver worked correctly
            case = cases_sorted[case_i]
            assignment[case["name"]] = bname
            schedule[bname].append([case["time"], case["time"]+case["duration"], case["location"], case["name"]])

    for bschedule in schedule.values():
        bschedule.sort()
    
    result["schedule"] = schedule
    result["assignment"] = assignment
    result["unassigned_cases"] = unassigned_cases
    return result