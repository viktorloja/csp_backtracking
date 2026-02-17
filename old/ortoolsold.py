from ortools.sat.python import cp_model

UNASSIGNED = "UNASSIGNED"

def build_full_travel_model(
    cases,
    barristers,
    travel_times,
    case_costs,
    *,
    lambda_travel=1,                # weight on travel objective
    day_start=0,                    # earliest departure time (minutes)
    day_end=24 * 60,                # latest return time (minutes)
    unassigned_penalty=10_000,      # allow leaving cases unassigned with penalty
    assignment_fixed=None,          # optional dict {case_name: barrister_name}
):
    """
    Fully considers travel costs:
      - home -> first event
      - event -> event (cases and fixed blocks)
      - last event -> home

    Scheduled blocks are modeled as mandatory events that MUST be visited
    in each barrister's path.

    Each case is either assigned to exactly one barrister OR marked UNASSIGNED.
    Objective = sum(case_cost) + lambda_travel * sum(travel_cost on chosen arcs) + unassigned penalties.
    """

    # ---- Helpers ----
    def travel(loc_a, loc_b):
        if loc_a == loc_b:
            return 0
        return travel_times.get((loc_a, loc_b), None)  # None => unknown / infeasible

    # Ensure cases are sorted by time (important for "forward arcs only" logic)
    cases_sorted = sorted(cases, key=lambda c: c["time"])
    num_cases = len(cases_sorted)

    barrister_names = [b["name"] for b in barristers]

    model = cp_model.CpModel()

    # ---- Assignment variables: assign[(case_index, barrister_name)] in {0,1} ----
    # Create assign vars only if seniority allows (basic feasibility).
    assign = {}
    for i, case in enumerate(cases_sorted):
        for b in barristers:
            if b.get("seniority", 0) < case.get("seniority", 0):
                continue
            assign[(i, b["name"])] = model.NewBoolVar(f"assign_case{i}_{case['name']}__to__{b['name']}")

    # Unassigned option for each case (so model is always feasible)
    unassigned = {}
    for i, case in enumerate(cases_sorted):
        unassigned[i] = model.NewBoolVar(f"unassigned_case{i}_{case['name']}")

    # Each case assigned to exactly one barrister OR unassigned
    for i in range(num_cases):
        possible = [assign[(i, bname)] for bname in barrister_names if (i, bname) in assign]
        model.Add(sum(possible) + unassigned[i] == 1)

    # Optional: fix some assignments
    if assignment_fixed:
        name_to_index = {c["name"]: i for i, c in enumerate(cases_sorted)}
        for case_name, bname in assignment_fixed.items():
            i = name_to_index[case_name]
            # force assigned to bname if possible; otherwise it'll be infeasible
            if (i, bname) not in assign:
                raise ValueError(f"Fixed assignment {case_name}->{bname} is impossible (no assign var).")
            model.Add(assign[(i, bname)] == 1)
            model.Add(unassigned[i] == 0)
            # force all other barristers = 0 for that case
            for other in barrister_names:
                if other != bname and (i, other) in assign:
                    model.Add(assign[(i, other)] == 0)

    # ---- Per-barrister route model (home start -> events -> home end) ----
    #
    # We create a set of "events" for each barrister:
    #   S: home_start (mandatory)
    #   blocks: each fixed schedule block (mandatory)
    #   cases: one event per case (optional; present iff assign(case,b)=1)
    #   T: home_end (mandatory)
    #
    # Then we create arc variables x[u,v] where u->v is allowed (forward in time and travel-feasible).
    # Constraints enforce a single path from S to T visiting all "present" events exactly once.

    all_travel_arc_terms = []  # travel_cost * arc_var, for objective

    for b in barristers:
        bname = b["name"]
        home_loc = b.get("home", "HOME")  # you should set this meaningfully

        # --- Build events list ---
        # We'll store arrays for readability:
        #   event_kind: "S", "BLOCK", "CASE", "T"
        #   start_time, end_time, location
        #   present_var: BoolVar or 1 for mandatory

        event_kind = []
        start_time = []
        end_time = []
        location = []
        present = []

        # Index 0: Home Start (S)
        event_kind.append("S")
        start_time.append(day_start)
        end_time.append(day_start)       # depart immediately
        location.append(home_loc)
        present.append(1)                # mandatory

        # Fixed schedule blocks (mandatory)
        # IMPORTANT: sort blocks by time
        blocks = sorted(b.get("schedule", []), key=lambda blk: blk["start_time"])
        for bi, blk in enumerate(blocks):
            event_kind.append("BLOCK")
            start_time.append(blk["start_time"])
            end_time.append(blk["end_time"])
            location.append(blk.get("location", home_loc))
            present.append(1)  # mandatory

        # Case events (optional): one per case
        # Presence = assign[(i,bname)] if that assignment exists, else 0 (cannot be assigned)
        case_event_index_for_case_i = {}  # map case i -> event index in this barrister's event list
        for i, case in enumerate(cases_sorted):
            event_kind.append("CASE")
            start_time.append(case["time"])
            end_time.append(case["time"] + case["duration"])
            location.append(case["location"])

            if (i, bname) in assign:
                p = assign[(i, bname)]
            else:
                # Can't assign this case to this barrister at all
                p = 0
            present.append(p)
            case_event_index_for_case_i[i] = len(event_kind) - 1

        # Index last: Home End (T)
        event_kind.append("T")
        start_time.append(day_end)
        end_time.append(day_end)
        location.append(home_loc)
        present.append(1)  # mandatory
        T_index = len(event_kind) - 1

        num_events = len(event_kind)

        # --- Create allowed forward arcs and arc vars ---
        # Allowed arcs:
        #   - from any event u (except T) to any later event v (except S)
        #   - must satisfy: end(u) + travel(u,v) <= start(v)
        #
        # For v == T (home end), we can optionally enforce end(u)+travel<=day_end (already implied by start(T)=day_end).
        #
        # NOTE: Because times are fixed and we only allow forward-in-time arcs, there are no cycles/subtours.

        arc = {}  # arc[(u,v)] = BoolVar if allowed

        # Precompute candidate pairs (u,v)
        for u in range(num_events):
            if u == T_index:
                continue  # no outgoing from T
            for v in range(num_events):
                if v == 0:
                    continue  # no incoming to S
                if v == u:
                    continue

                # forward in time: must start later (or equal is okay only if feasible, but usually not)
                if start_time[v] < end_time[u]:
                    continue

                tcost = travel(location[u], location[v])
                if tcost is None:
                    continue

                # time feasibility
                if end_time[u] + tcost > start_time[v]:
                    continue

                arc[(u, v)] = model.NewBoolVar(f"arc__{bname}__{u}_to_{v}")

        # Also allow the trivial direct arc S->T (if feasible)
        if (0, T_index) not in arc:
            tcost = travel(location[0], location[T_index])
            if tcost is None:
                # If missing travel HOME->HOME, assume 0
                tcost = 0
            if end_time[0] + tcost <= start_time[T_index]:
                arc[(0, T_index)] = model.NewBoolVar(f"arc__{bname}__S_to_T")

        # --- Flow / path constraints ---
        # For each event e:
        #   sum_in(e)  == present(e)   for e != S
        #   sum_out(e) == present(e)   for e != T
        #
        # For S: sum_out(S) == 1
        # For T: sum_in(T) == 1
        #
        # This forces a single path from S to T that visits every present node exactly once.
        # In a forward-time DAG, disjoint chains are impossible because every present node
        # needs exactly one predecessor and one successor, and only S can have no predecessor
        # and only T can have no successor.

        # Build incoming/outgoing lists for each node
        incoming = [[] for _ in range(num_events)]
        outgoing = [[] for _ in range(num_events)]
        for (u, v), x in arc.items():
            outgoing[u].append(x)
            incoming[v].append(x)

        # S constraints
        model.Add(sum(outgoing[0]) == 1)   # leave home once
        model.Add(sum(incoming[0]) == 0)   # nobody enters S

        # T constraints
        model.Add(sum(incoming[T_index]) == 1)  # arrive home once
        model.Add(sum(outgoing[T_index]) == 0)  # nobody leaves T

        # Internal event constraints
        for e in range(1, T_index):
            # present[e] can be 1, 0, or a BoolVar (assignment var)
            p = present[e]

            # If p is 0 (cannot be present), force no in/out
            if p == 0:
                model.Add(sum(incoming[e]) == 0)
                model.Add(sum(outgoing[e]) == 0)
                continue

            # If p is constant 1 (mandatory block), require exactly one in/out
            if p == 1:
                model.Add(sum(incoming[e]) == 1)
                model.Add(sum(outgoing[e]) == 1)
            else:
                # p is BoolVar (case assigned to this barrister)
                model.Add(sum(incoming[e]) == p)
                model.Add(sum(outgoing[e]) == p)

        # --- Travel objective terms for this barrister ---
        for (u, v), x in arc.items():
            tcost = travel(location[u], location[v])
            if tcost is None:
                continue
            all_travel_arc_terms.append(tcost * x)

    # ---- Cost objective terms ----
    case_cost_terms = []
    for i, case in enumerate(cases_sorted):
        cname = case["name"]

        # assignment costs
        for bname in barrister_names:
            if (i, bname) in assign:
                cost = case_costs.get((cname, bname), 999999)
                case_cost_terms.append(cost * assign[(i, bname)])

        # unassigned penalty
        case_cost_terms.append(unassigned_penalty * unassigned[i])

    model.Minimize(sum(case_cost_terms) + lambda_travel * sum(all_travel_arc_terms))
    return model, assign, unassigned, cases_sorted


def solve_full_travel_model(model, assign, unassigned, cases_sorted, max_time_seconds=10):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_seconds
    status = solver.Solve(model)

    result = {
        "status": solver.StatusName(status),
        "objective": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "assignment": None,
        "unassigned_cases": None,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return result

    assignment = {}
    unassigned_cases = []

    for i, case in enumerate(cases_sorted):
        if solver.Value(unassigned[i]) == 1:
            unassigned_cases.append(case["name"])
            continue
        for (ii, bname), var in assign.items():
            if ii == i and solver.Value(var) == 1:
                assignment[case["name"]] = bname
                break

    result["assignment"] = assignment
    result["unassigned_cases"] = unassigned_cases
    return result

from ortools.sat.python import cp_model
from bisect import bisect_right

UNASSIGNED = "UNASSIGNED"

def build_model_with_pruned_assignments(
    cases,
    barristers,
    travel_times,
    case_costs,
    *,
    day_start=0,
    day_end=24 * 60,
    unassigned_penalty=10_000,
    assignment_fixed=None,   # dict {case_name: barrister_name}
):
    """
    Builds ONLY the assignment variables (and the per-case 'unassigned' var),
    using binary search against each barrister's mandatory events (home + blocks + home).

    You can then plug (assign, unassigned, cases_sorted) into your full route-building code.

    Returns:
      model, cases_sorted, assign, unassigned, mandatory_by_barrister
    """
    model = cp_model.CpModel()

    cases_sorted = sorted(cases, key=lambda c: c["time"])
    case_index = {c["name"]: i for i, c in enumerate(cases_sorted)}

    # ---- travel lookup (directional) ----
    def travel(loc_a, loc_b):
        if loc_a == loc_b:
            return 0
        return travel_times.get((loc_a, loc_b), None)

    # ---- Build mandatory events per barrister ----
    # Each mandatory event is a dict: {"start":..., "end":..., "loc":...}
    # We also store a list of starts for binary search.
    mandatory_by_b = {}
    mandatory_starts_by_b = {}

    for b in barristers:
        bname = b["name"]
        home = b.get("home", "HOME")

        blocks = sorted(b.get("schedule", []), key=lambda blk: blk["start_time"])

        mandatory = [{"start": day_start, "end": day_start, "loc": home}]
        for blk in blocks:
            mandatory.append({
                "start": blk["start_time"],
                "end": blk["end_time"],
                "loc": blk.get("location", home),
            })
        mandatory.append({"start": day_end, "end": day_end, "loc": home})

        # Sanity: ensure non-decreasing by start
        # (If blocks overlap, the model may be infeasible; you might want to validate earlier.)
        mandatory_by_b[bname] = mandatory
        mandatory_starts_by_b[bname] = [e["start"] for e in mandatory]

    # ---- Binary-search feasibility test (case must fit in ONE mandatory gap) ----
    def case_fits_mandatory_gap(case, bname):
        """
        Returns True iff case can be inserted between two consecutive mandatory events
        that surround the case by time, using travel feasibility on both sides.
        O(log #blocks) via binary search.
        """
        m = mandatory_by_b[bname]
        starts = mandatory_starts_by_b[bname]

        c_start = case["time"]
        c_end = c_start + case["duration"]
        c_loc = case["location"]

        # Find the rightmost mandatory event with start <= c_start
        # idx is in [0, len(m)-1]
        idx = bisect_right(starts, c_start) - 1
        if idx < 0:
            idx = 0
        if idx >= len(m) - 1:
            # case starts after home_end start -> can't fit
            return False

        prev_ev = m[idx]
        next_ev = m[idx + 1]

        # Must be time-contained by the gap (ignoring travel first):
        if not (prev_ev["end"] <= c_start and c_end <= next_ev["start"]):
            return False

        # Must have travel feasible on both legs:
        t_prev = travel(prev_ev["loc"], c_loc)
        if t_prev is None:
            return False

        t_next = travel(c_loc, next_ev["loc"])
        if t_next is None:
            return False

        if prev_ev["end"] + t_prev > c_start:
            return False
        if c_end + t_next > next_ev["start"]:
            return False

        return True

    # ---- Create assignment vars with pruning ----
    assign = {}      # (case_i, barrister_name) -> BoolVar
    unassigned = {}  # case_i -> BoolVar

    for i, case in enumerate(cases_sorted):
        cname = case["name"]
        required_b = assignment_fixed.get(cname) if assignment_fixed else None

        # Always create unassigned var (even if fixed, we just pin it to 0)
        unassigned[i] = model.NewBoolVar(f"unassigned__{cname}")

        feasible_assign_vars = []

        if required_b is not None:
            # Only create the fixed barrister var and force it to 1
            # (Also: we still sanity-check that it is feasible.)
            bname = required_b
            # Locate barrister record
            b_rec = next((bb for bb in barristers if bb["name"] == bname), None)
            if b_rec is None:
                raise ValueError(f"Fixed assignment refers to unknown barrister: {bname}")

            if b_rec.get("seniority", 0) < case.get("seniority", 0):
                raise ValueError(f"Fixed assignment {cname}->{bname} violates seniority requirement.")

            if not case_fits_mandatory_gap(case, bname):
                raise ValueError(f"Fixed assignment {cname}->{bname} cannot fit around mandatory blocks/home.")

            v = model.NewBoolVar(f"assign__{cname}__to__{bname}")
            assign[(i, bname)] = v
            model.Add(v == 1)
            model.Add(unassigned[i] == 0)
            # No need to add the ==1 constraint below, but it’s fine to keep consistent
            continue

        # Non-fixed case: create assign vars only if they pass seniority + gap feasibility
        for b in barristers:
            bname = b["name"]

            if b.get("seniority", 0) < case.get("seniority", 0):
                continue

            # Prune impossible pairings quickly
            if not case_fits_mandatory_gap(case, bname):
                continue

            v = model.NewBoolVar(f"assign__{cname}__to__{bname}")
            assign[(i, bname)] = v
            feasible_assign_vars.append(v)

        # Each case assigned to exactly 1 barrister OR unassigned
        model.Add(sum(feasible_assign_vars) + unassigned[i] == 1)

        # If literally no barrister can take it, force unassigned
        if not feasible_assign_vars:
            model.Add(unassigned[i] == 1)

    # Objective terms (just assignment + unassigned penalty here)
    # Your full model will add travel arcs in the objective later.
    cost_terms = []
    for i, case in enumerate(cases_sorted):
        cname = case["name"]

        cost_terms.append(unassigned_penalty * unassigned[i])

        for (ii, bname), var in assign.items():
            if ii != i:
                continue
            cost = case_costs.get((cname, bname), 999999)
            cost_terms.append(cost * var)

    model.Minimize(sum(cost_terms))

    return model, cases_sorted, assign, unassigned, mandatory_by_b

#####

# USE THIS ONE