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


def greedy(
    cases,
    barristers,
    travel_times,
    case_costs,
    assignment_fixed,
    day_start=0,
    day_end=24 * 60,
    unassigned_penalty=10_000,
):

    def travel(loc_a, loc_b):
        if loc_a == loc_b:
            return 0
        return travel_times.get((loc_a, loc_b), None)
    
    def feasible(
        case,
        timeline,
        timeline_starts
    ):
        """
        O(log #blocks) using bisect on mandatory starts.
        Returns True if case can fit between two consecutive mandatory events around its start time,
        with travel feasibility on both sides.
        """

        c_start = case["time"]
        c_end = c_start + case["duration"]
        c_loc = case["location"]

        # Find the rightmost mandatory event with start <= c_start
        idx = bisect_right(timeline_starts, c_start)

        if idx == 0 or idx == len(timeline):
            return None, None  # outside barrister's working times

        prev_event = timeline[idx-1]
        next_event = timeline[idx]

        prev_end, prev_loc = prev_event.end, prev_event.location
        next_start, next_loc = next_event.start, next_event.location

        # Must lie within the time gap (ignoring travel first)
        if not (prev_end <= c_start and c_end <= next_start):
            return None, None

        t_prev = travel(prev_loc, c_loc)
        t_next = travel(c_loc, next_loc)
        t_prev_next = travel(prev_loc, next_loc)

        if prev_end + t_prev > c_start:
                return None, None
        if c_end + t_next > next_start:
                return None, None
        
        delta = t_prev + t_next - t_prev_next
        return delta, idx

    base, base_starts = build_base_timelines(barristers)
    total_score = 0
    assignment = {}

    for barrister in barristers:
        bname = barrister["name"]
        b_base = base[bname]
        for i in range(len(b_base)-1):
            total_score += travel(b_base[i].location, b_base[i+1].location)

    
    for case in cases:
        cname = case["name"]
        best = unassigned_penalty
        chosen_barrister = UNASSIGNED
        curr_delta = 0
        curr_idx = None
        if cname not in assignment_fixed:
            for barrister in barristers:

                bname = barrister["name"]
                delta, idx = feasible(case, base[bname], base_starts[bname])

                if delta:

                    if case_costs[(cname, bname)] < best:
                        best = case_costs[(cname, bname)]
                        chosen_barrister = bname
                        curr_delta = delta
                        curr_idx = idx

            if curr_idx:
                event = Event(case["time"], case["time"] + case["duration"], case["location"], cname)
                base[chosen_barrister].insert(curr_idx, event)
                base_starts[chosen_barrister].insert(curr_idx, case["time"])
                total_score += (curr_delta + best)
                assignment[cname] = chosen_barrister

        else:

            bname = assignment_fixed[cname]
            delta, idx = feasible(case, base[bname], base_starts[bname])
            case_cost = case_costs[(cname, bname)]

            event = Event(case["time"], case["time"] + case["duration"], case["location"], cname)
            base[bname].insert(idx, event)
            base_starts[bname].insert(idx, case["time"])
            total_score += (delta + case_cost)
            assignment[cname] = bname


    return assignment, base, total_score

        
            

