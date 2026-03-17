from bisect import bisect_right
from bisect import bisect_left
from typing import NamedTuple

class Event(NamedTuple):
    start: int
    end: int
    location: str
    name: str

UNASSIGNED = "UNASSIGNED"



def local_search(barristers, cases, assignments, timelines, timelines_starts, case_costs, travel_times, current_score):

    case_by_name = {}
    for case in cases:
        case_by_name[case["name"]] = case


    def travel(loc_a, loc_b):
        if loc_a == loc_b:
            return 0
        return travel_times.get((loc_a, loc_b), None)

    def case_fits(
        case,
        timeline,           # list of events, sorted by start time
        timeline_starts
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
            return None  # outside barrister's working times

        prev_ev = timeline[idx-1]
        next_ev = timeline[idx]

        prev_end, prev_loc = prev_ev.end, prev_ev.location
        next_start, next_loc = next_ev.start, next_ev.location

        t_prev = travel(travel_times, prev_loc, c_loc)
        t_next = travel(travel_times, c_loc, next_loc)
        if t_prev is None or t_next is None:
            return None
        
        # feasibility
        if prev_end + t_prev > c_start:
            return None
        if c_end + t_next > next_start:
            return None

        return idx
    

    def find_case(bname, time):
        # binary search for case time then return index
        timeline_starts = timelines_starts[bname]
        idx = bisect_left(timeline_starts, time)
        return idx
        

    def remove_case(bname, cname, index):
       
        timeline = timelines[bname]
        cost = -case_costs[(bname, cname)]
        cost -= travel(timeline[index-1].location, timeline[index].location)
        cost -= travel(timeline[index].location, timeline[index+1].location)
        cost += travel(timeline[index-1].location, timeline[index+1].location)
        return cost

    def add_case(bname, case, index):
        cname = case["name"]
        cloc = case["location"]

        timeline = timelines[bname]
        cost = case_costs[(bname, cname)]
        cost += travel(timeline[index-1].location, cloc)
        cost += travel(cloc, timeline[index].location)
        cost -= travel(timeline[index-1].location, timeline[index].location)
        return cost


    def relocate(assignment):
        best_cost = 0
        best_barrister = None
        best_index = None

        for cname, bname in assignment:
            if bname != UNASSIGNED:
                #cost change for removing
                case = case_by_name[cname]

                time = case["time"]
                old_index = find_case(bname, time)
                cost_back = remove_case(bname, cname, old_index)

                for new_barrister in barristers:
                    if new_barrister["seniority"] >= case["seniority"]:
                        new_index = case_fits(case, timelines[new_barrister["name"]], timelines_starts[new_barrister["name"]])
                        if new_index != None:
                            new_cost = add_case(new_barrister["name"], case, new_index)
                            cost_change = new_cost + cost_back
                           
                            if cost_change < best_cost:
                                best_cost = cost_change
                                best_barrister = new_barrister["name"]
                                best_index = new_index
            
                if best_cost < 0:
                    # pop case from timeline of old barrister
                    # insert case into timeline of new barrister
                    timelines[bname].pop(old_index)
                    timelines_starts[bname].pop(old_index)

                    ev = Event(case["time"], case["time"] + case["duration"], case["location"], "CASE")
                    timelines[best_barrister].insert(best_index, ev)
                    timelines_starts[best_barrister].insert(best_index, case["time"])

                    return best_cost
        
        return best_cost
        
    def swap():
        length = len(assignments)
        for i in range(length):
            for j in range(i+1, length):
                cname1, bname1, = assignments[i]
                cname2, bname2 = assignments[j]
                if bname1 != UNASSIGNED and bname2 != UNASSIGNED:
                
                    case1 = case_by_name[cname1]
                    case2 = case_by_name[cname2]

                    timeline1 = timelines[bname1]
                    timeline2 = timelines[bname2]
                    timeline_start1 = timelines_starts[bname1]
                    timeline_start2 = timelines_starts[bname2]
    
                    old_index1 = find_case(bname1, case1["time"])
                    old_index2 = find_case(bname2, case2["time"])
            
                    new_cost = remove_case(bname1, cname1, old_index1) + remove_case(bname2, cname2, old_index2)

                    # pop old case from each of timelines
                    timeline1.pop(old_index1)
                    timeline_start1.pop(old_index1)
                    timeline2.pop(old_index2)
                    timeline_start2.pop(old_index2)

                    # test to see if new cases fit
                    new_index1 = case_fits(case2, timeline1, timeline_start1)
                    new_index2 = case_fits(case1, timeline2, timeline_start2)

                    if new_index1 != None and new_index2 != None:
                        #insert case
                        
                        new_cost += (add_case(bname1, case2, new_index1) + add_case(bname2, case1, new_index2))
                        if new_cost < 0:
                            
                            ev = Event(case2["time"], case2["time"] + case2["duration"], case2["location"], "CASE")
                            timeline1.insert(new_index1, ev)
                            timeline_start1.insert(new_index1, case2["time"])

                            ev = Event(case1["time"], case1["time"] + case1["duration"], case1["location"], "CASE")
                            timeline2.insert(new_index2, ev)
                            timeline_start2.insert(new_index2, case1["time"])

                            return new_cost
                        
                    ev = Event(case1["time"], case1["time"] + case1["duration"], case1["location"], "CASE")
                    timeline1.insert(old_index1, ev)
                    timeline_start1.insert(old_index1, case1["time"])

                    ev = Event(case2["time"], case2["time"] + case2["duration"], case2["location"], "CASE")
                    timeline2.insert(old_index2, ev)
                    timeline_start2.insert(old_index2, case1["time"])


              

        
    improvement = True
    while improvement:
        improvement = False
        cost_change = relocate(assignments)
        if cost_change < 0:
            improvement = True
            current_score += cost_change
        else:
            cost_change = swap(assignments)
            if cost_change < 0:
                improvement = True
                current_score += cost_change

    return assignments, timelines, current_score





  