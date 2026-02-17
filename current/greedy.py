from math import inf
from bisect import bisect_left
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

def travel_time(travel_times, loc_a, loc_b):
    if loc_a == loc_b:
        return 0
    return travel_times.get((loc_a, loc_b), None)

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
    c_end = c_start + case["duration"]
    c_loc = case["location"]

    # find insertion point by start time
    idx = bisect_left(timeline_starts, c_start)

    prev_ev = timeline[idx - 1] 
    next_ev = timeline[idx]

    prev_end, prev_loc = prev_ev.end, prev_ev.location
    next_start, next_loc = next_ev.start, next_ev.location

    # delta travel
    t_prev = travel_time(travel_times, prev_loc, c_loc)
    t_next = travel_time(travel_times, c_loc, next_loc)
    t_prev_next = travel_time(travel_times, prev_loc, next_loc)

    if prev_end + t_prev > c_start:
            return None
    if c_end + t_next > next_start:
            return None
    
    delta = t_prev + t_next - t_prev_next
    return delta, idx

def greedy(
    cases,
    barristers,
    travel_times,
    case_costs,
    assignment_fixed = {},
    day_start=0,
    day_end=24 * 60,
    unassigned_penalty=10_000,
):
    schedule = []
    base, base_starts = build_base_timelines(barristers)

    def travel(loc_a, loc_b):
        if loc_a == loc_b:
            return 0
        return travel_times.get((loc_a, loc_b), None)
    
    def feasible(case, bname):
        """
        O(log #blocks) using bisect on mandatory starts.
        Returns True if case can fit between two consecutive mandatory events around its start time,
        with travel feasibility on both sides.
        """
        blocks = base[bname]
        starts = base_starts[bname]

        c_start = case["time"]
        c_end = c_start + case["duration"]
        c_loc = case["location"]

        # Find the rightmost mandatory event with start <= c_start
        idx = bisect_right(starts, c_start) - 1
        if idx < 0:
            idx = 0
        if idx >= len(blocks) - 1:
            return None  # beyond barrister end time

        prev_event = blocks[idx]
        next_event = blocks[idx + 1]

        # Must lie within the time gap (ignoring travel first)
        if not (prev_event.end <= c_start and c_end <= next_event.start):
            return None

        t_prev = travel(prev_event.location, c_loc)
        t_next = travel(c_loc, next_event.location)
        if t_prev is None or t_next is None:
            return None

        if prev_event.end + t_prev > c_start:
            return None
        if c_end + t_next > next_event.start:
            return None

        return idx

    for case in cases:
        cname = case["name"]
        best = unassigned_penalty
        chosen_barrister = UNASSIGNED
        if cname not in assignment_fixed:
            for barrister in barristers:
                if feasible(case, barrister):
                    bname = barrister["name"]
                    if case_costs[(cname, bname)] < best:
                        best = case_costs[(cname, bname)]
                        chosen_barrister = bname

                base[bname].insert(idx, ev)
                inserted = True

