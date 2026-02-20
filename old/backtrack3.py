from math import inf
from bisect import bisect_left
from typing import NamedTuple

class Event(NamedTuple):
    start: int
    end: int
    location: str
    name: str

UNASSIGNED = "UNASSIGNED"

def build_base_timelines(barristers, day_start=0, day_end=24*60):
    """
    For each barrister, create a base timeline of mandatory events:
      HOME_START, scheduled blocks, HOME_END
    Each event is a tuple: (start, end, location, kind, name)
    Sorted by start time.
    """
    base = {}
    base_starts = {}
    for b in barristers:
        bname = b["name"]
        home = b["home"]
        blocks = b.get("schedule", [])

        events = [Event(day_start, day_start, home, "HOME_START")]
        for blk in blocks:
            events.append(Event(
                blk["start_time"],
                blk["end_time"],
                blk.get("location", home),
                "BLOCKED"
            ))
        events.append(Event(day_end, day_end, home, "HOME_END"))

        base[bname] = events
        base_starts[bname] = [e.start for e in events]

    return base, base_starts

def travel_time(travel_times, loc_a, loc_b):
    if loc_a == loc_b:
        return 0
    return travel_times.get((loc_a, loc_b), None)

def try_insert_case_get_delta(
    case_name,
    barrister_name,
    timeline,           # list of events, sorted by start time
    timeline_starts,
    cases_by_name,
    travel_times
):
    """
    Attempt to insert case event into barrister timeline.
    Returns (feasible, delta_travel, insert_index, prev_event, next_event)

    timeline events: (start, end, loc, kind, name)
    case event:      (c_start, c_end, c_loc, "CASE", case_name)
    """
    c = cases_by_name[case_name]
    c_start = c["time"]
    c_end = c_start + c["duration"]
    c_loc = c["location"]

    # find insertion point by start time
    idx = bisect_left(timeline_starts, c_start)

    prev_ev = timeline[idx - 1] if idx - 1 >= 0 else None
    next_ev = timeline[idx] if idx < len(timeline) else None

    # must have prev and next because we include HOME_START and HOME_END
    if prev_ev is None or next_ev is None:
        return False, inf, idx, prev_ev, next_ev

    prev_end, prev_loc = prev_ev.end, prev_ev.location
    next_start, next_loc = next_ev.start, next_ev.location

    t_prev = travel_time(travel_times, prev_loc, c_loc)
    t_next = travel_time(travel_times, c_loc, next_loc)
    if t_prev is None or t_next is None:
        return False, inf, idx, prev_ev, next_ev

    # feasibility
    if prev_end + t_prev > c_start:
        return False, inf, idx, prev_ev, next_ev
    if c_end + t_next > next_start:
        return False, inf, idx, prev_ev, next_ev

    # delta travel
    t_prev_next = travel_time(travel_times, prev_loc, next_loc)
    if t_prev_next is None:
        # if missing, treat as infeasible to keep model consistent
        return False, inf, idx, prev_ev, next_ev

    delta = t_prev + t_next - t_prev_next
    return True, delta, idx, prev_ev, next_ev

def lower_bound_case_cost_only(remaining_cases, domains, cost_lookup):
    """
    Safe bound: ignore travel, sum min assignment cost over remaining cases.
    cost_lookup[(case,b)] must exist for b in domains[case].
    """
    bnd = 0
    for case in remaining_cases:
        bnd += min(cost_lookup[(case, b)] for b in domains[case])
    return bnd

def branch_and_bound_travel(
    cases,
    barristers,
    travel_times,
    case_costs,                # dict {(case_name, barrister_name): cost}
    domains,                   # dict {case_name: [barrister_names...]}
    constraints=None,          # optional; you can ignore or keep for extra pruning
    *,
    lambda_travel=1.0,
    unassigned_penalty=10_000,
    day_start=0,
    day_end=24*60,
):
    """
    Returns best_solution, best_cost.
    best_solution maps case_name -> barrister_name or UNASSIGNED.
    """

    cases_by_name = {c["name"]: c for c in cases}
    timelines, timelines_starts = build_base_timelines(barristers, day_start, day_end)

    # Add UNASSIGNED option to every domain (if not already)
    for cname in domains:
        if UNASSIGNED not in domains[cname]:
            domains[cname] = list(domains[cname]) + [UNASSIGNED]
        # define cost for unassigned
        case_costs[(cname, UNASSIGNED)] = unassigned_penalty

    neighbours = {c["name"]: set() for c in cases}
    if constraints:
        for (x, y) in constraints:
            neighbours[x].add(y)

    best_solution = None
    best_cost = inf

    # mutable state during search
    assignment = {}
    #timelines = {b["name"]: list(base_timelines[b["name"]]) for b in barristers}

    remaining = set(domains.keys())

    # heuristic: degree for tie-break
    def choose_next_case(rem):
        # MRV + degree tie-break
        return min(rem, key=lambda c: (len(domains[c]), -len(neighbours.get(c, ()))))

    def order_values(case):
        # LCV-ish: sort by incremental (case_cost + lambda*delta_travel)
        vals = []
        for b in domains[case]:
            if b == UNASSIGNED:
                vals.append((case_costs[(case, UNASSIGNED)], UNASSIGNED, 0.0, None))
                continue
            feasible, delta, idx, _, _ = try_insert_case_get_delta(case, b, timelines[b], timelines_starts[b], cases_by_name, travel_times)
            if not feasible:
                continue
            inc = case_costs[(case, b)] + lambda_travel * delta
            vals.append((inc, b, delta, idx))
        vals.sort(key=lambda x: x[0])
        return vals

    def dfs(rem_cases, current_cost):
        nonlocal best_solution, best_cost

        if not rem_cases:
            if current_cost < best_cost:
                best_cost = current_cost
                best_solution = assignment.copy()
            return

        # bound prune
        bnd = current_cost + lower_bound_case_cost_only(rem_cases, domains, case_costs)
        if bnd >= best_cost:
            return

        case = choose_next_case(rem_cases)

        candidates = order_values(case)
        if not candidates:
            # no feasible barrister (shouldn't happen because UNASSIGNED is always feasible)
            assignment[case] = UNASSIGNED
            dfs(rem_cases - {case}, current_cost + case_costs[(case, UNASSIGNED)])
            del assignment[case]
            return

        # small extra prune: if best possible for this case already too large
        if current_cost + candidates[0][0] >= best_cost:
            return

        for inc, b, delta, idx in candidates:
            new_cost = current_cost + inc
            if new_cost >= best_cost:
                break  # candidates sorted by inc

            assignment[case] = b

            inserted = False
            if b != UNASSIGNED:
                # insert event
                c = cases_by_name[case]
                ev = Event(c["time"], c["time"] + c["duration"], c["location"], "CASE")
                timelines[b].insert(idx, ev)
                inserted = True

            dfs(rem_cases - {case}, new_cost)

            # undo
            if inserted:
                timelines[b].pop(idx)
            del assignment[case]

    dfs(remaining, 0.0)
    return best_solution, best_cost
