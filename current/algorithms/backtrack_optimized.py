from math import inf
from bisect import bisect_right
from typing import NamedTuple

class Event(NamedTuple):
    start: int
    end: int
    location: str
    name: str

UNASSIGNED = "UNASSIGNED"

def build_base_timelines(barristers):
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
        day_start = b["day_start"]
        day_end = b["day_end"]
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


def travel(travel_times, loc_a, loc_b):
    if loc_a == loc_b:
        return 0
    return travel_times.get((loc_a, loc_b), None)


def calculate_initial_cost(timelines, travel_times):
    initial_cost = 0
    for schedule in timelines.values():
        for i in range(len(schedule)-1):
            initial_cost += travel(travel_times, schedule[i].location, schedule[i+1].location)
    return initial_cost


def case_insert_cost(
    case,
    timeline,           # list of events, sorted by start time
    timeline_starts,
    travel_times
):
    """
    Find index where case would be inserted into barrister timeline
    Calculate the delta (change in total travel time)
    """

    c_start = case["time"]
    #c_end = c_start + c["duration"]
    c_loc = case["location"]

    # find insertion point by start time
    idx = bisect_right(timeline_starts, c_start)

    prev_ev = timeline[idx - 1] 
    next_ev = timeline[idx]

    prev_end, prev_loc = prev_ev.end, prev_ev.location
    next_start, next_loc = next_ev.start, next_ev.location

    # delta travel
    t_prev = travel(travel_times, prev_loc, c_loc)
    t_next = travel(travel_times, c_loc, next_loc)
    t_prev_next = travel(travel_times, prev_loc, next_loc)

    delta = t_prev + t_next - t_prev_next
    return delta, idx

def lower_bound_case_cost_only(remaining_cases, domains, cost_lookup):
    """
    Safe bound: ignore travel, sum min assignment cost over remaining cases.
    cost_lookup[(case,b)] must exist for b in domains[case].
    """
    bnd = 0
    for case in remaining_cases:
        bnd += min(cost_lookup[(case, b)] for b in domains[case])
    return bnd

def branch_and_bound(
    cases,
    timelines,
    timelines_starts,
    travel_times,
    case_costs,                # dict {(case_name, barrister_name): cost}
    domains,                   # dict {case_name: [barrister_names...]}            
    constraints,        
    *,
    lambda_travel=1.0,
    unassigned_penalty=10_000,
):
    """
    Returns best_solution, best_cost.
    best_solution maps case_name -> barrister_name or UNASSIGNED.
    """

    cases_by_name = {c["name"]: c for c in cases}

    # Add UNASSIGNED option to every domain (if not already)
    for cname in domains:
        domains[cname].add(UNASSIGNED)
        case_costs[(cname, UNASSIGNED)] = unassigned_penalty

    neighbours = {c["name"]: set() for c in cases}
    if constraints:
        for (x, y) in constraints:
            neighbours[x].add(y)
            neighbours[y].add(x)

    best_solution = None
    best_cost = inf

    # mutable state during search
    assignment = {}
    remaining = set(domains.keys())

    # heuristic: degree for tie-break
    def choose_next_case(rem):
        # MRV + degree tie-break
        return min(rem, key=lambda c: (len(domains[c]), -len(neighbours.get(c, ()))))

    def order_values(cname, case):
        # LCV-ish: sort by incremental (case_cost + lambda*delta_travel)
        vals = []
        for b in domains[cname]:
            if b == UNASSIGNED:
                vals.append((case_costs[(cname, UNASSIGNED)], UNASSIGNED, None))
                continue
            delta, idx = case_insert_cost(case, timelines[b], timelines_starts[b], travel_times)
            inc = case_costs[(cname, b)] + lambda_travel * delta
            vals.append((inc, b, idx))
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

        cname = choose_next_case(rem_cases)
        case = cases_by_name[cname]
        candidates = order_values(cname, case)

        # small extra prune: if best possible for this case already too large
        if current_cost + candidates[0][0] >= best_cost:
            return

        for inc, b, idx in candidates:
            new_cost = current_cost + inc
            if new_cost >= best_cost:
                break  # candidates sorted by inc

            assignment[cname] = b
            # remove b from domains of conflicting cases
            for neighbour in neighbours[cname]:
                if b in domains[neighbour]:
                    domains[neighbour].remove(b)


            inserted = False
            if b != UNASSIGNED:
                # insert event
                c = cases_by_name[cname]
                ev = Event(c["time"], c["time"] + c["duration"], c["location"], "CASE")
                timelines[b].insert(idx, ev)
                inserted = True

            dfs(rem_cases - {cname}, new_cost)

            # undo
            if inserted:
                timelines[b].pop(idx)

            for neighbour in neighbours[cname]:
                domains[neighbour].add(b)

            del assignment[cname]

    dfs(remaining, calculate_initial_cost(timelines, travel_times))
    return best_solution, best_cost, timelines

def case_fits(
    case,
    timeline,           # list of events, sorted by start time
    timeline_starts,
    travel_times
):
    """
    Attempt to insert case event into barrister timeline.
    Returns (feasible, delta_travel, insert_index, prev_event, next_event)

    timeline events: (start, end, loc, kind, name)
    case event:      (c_start, c_end, c_loc, "CASE", case_name)
    """
    c_start = case["time"]
    c_end = c_start + case["duration"]
    c_loc = case["location"]

    # Find the rightmost mandatory event with start <= c_start
    idx = bisect_right(timeline_starts, c_start)

    if idx == 0 or idx == len(timeline):
        return False  # outside barrister's working times

    prev_ev = timeline[idx-1]
    next_ev = timeline[idx]

    prev_end, prev_loc = prev_ev.end, prev_ev.location
    next_start, next_loc = next_ev.start, next_ev.location

    t_prev = travel(travel_times, prev_loc, c_loc)
    t_next = travel(travel_times, c_loc, next_loc)
    if t_prev is None or t_next is None:
        return False
    
    # feasibility
    if prev_end + t_prev > c_start:
        return False
    if c_end + t_next > next_start:
        return False

    return True


def define_inputs(cases, barristers, travel_times):
    n = len(cases)
    timelines, timelines_starts = build_base_timelines(barristers)

    domains = {}
    constraints = set()

    for case in cases:
        cname = case["name"]
        domains[cname] = set()
        for barrister in barristers:
            if barrister["seniority"] >= case["seniority"]:
                bname = barrister["name"]
                if case_fits(case, timelines[bname], timelines_starts[bname], travel_times):
                    domains[cname].add(bname)

    for i in range(n-1):
        for j in range(i+1, n):
            case1 = cases[i]
            case2 = cases[j]
            cname1 = case1["name"]
            cname2 = case2["name"]
            if (case2["time"] - case1["time"]) < (travel_times[(case1["location"], case2["location"])] + case1["duration"]): #if cases are too close together considering travel and case time
                # add constraint, case1 and case2 cannot have same barrister
                constraints.add((cname1, cname2))

    return domains, constraints, timelines, timelines_starts