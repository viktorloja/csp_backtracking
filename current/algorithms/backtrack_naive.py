from math import inf
from bisect import bisect_left
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
    idx = bisect_left(timeline_starts, c_start)

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


def branch_and_bound_naive(
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
    #for cname in domains:
        #domains[cname].add(UNASSIGNED)
        #case_costs[(cname, UNASSIGNED)] = unassigned_penalty

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

    def dfs(rem_cases, current_cost):
        nonlocal best_solution, best_cost
        print(best_cost)

        if not rem_cases:
            if current_cost < best_cost:
                best_cost = current_cost
                best_solution = assignment.copy()
            return

        for cname in rem_cases:
            case = cases_by_name[cname]
            for bname in domains[cname]:
                    
                delta, idx = case_insert_cost(case, timelines[bname], timelines_starts[bname], travel_times)
                inc = delta + case_costs[(cname, bname)]
                new_cost = current_cost + inc
                if new_cost >= best_cost: # skip early if already bad solution
                    continue

                assignment[cname] = bname
                # remove barrister from domains of conflicting cases
                removed = []
                for neighbour in neighbours[cname]:
                    if bname in domains[neighbour]:
                        domains[neighbour].remove(bname)
                        removed.append(neighbour)


                inserted = False
                if bname != UNASSIGNED:
                    # insert event
                    c = cases_by_name[cname]
                    ev = Event(case["time"], case["time"] + case["duration"], case["location"], cname)
                    timelines[bname].insert(idx, ev)
                    timelines_starts[bname].insert(idx, case["time"])
                    inserted = True

                dfs(rem_cases - {cname}, new_cost)

                # undo
                if inserted:
                    timelines[bname].pop(idx)
                    timelines_starts[bname].pop(idx)

                for neighbour in removed:
                    domains[neighbour].add(bname)

                del assignment[cname]

            new_cost = current_cost + unassigned_penalty
            if new_cost < best_cost:
                assignment[cname] = UNASSIGNED
                dfs(rem_cases - {cname}, new_cost)
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

    # find insertion point by start time
    idx = bisect_left(timeline_starts, c_start)

    prev_ev = timeline[idx - 1] if idx - 1 >= 0 else None
    next_ev = timeline[idx] if idx < len(timeline) else None

    # must have prev and next because we include HOME_START and HOME_END
    if prev_ev is None or next_ev is None:
        return False

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