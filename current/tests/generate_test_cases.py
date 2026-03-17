import random
import math
from typing import Dict, List, Tuple, Optional


# ============================================================
# 1) LOCATION + SYMMETRIC TRAVEL TIMES
# ============================================================

def make_locations(num_locations: int, seed: int) -> Tuple[List[str], Dict[str, Tuple[float, float]]]:
    """
    Create:
      - locations: ["L0", "L1", ...]
      - coords: { "L0": (x,y), ... } with random coordinates in [0,1]x[0,1]

    We use coords to derive travel times based on Euclidean distance.
    """
    rng = random.Random(seed)
    locations = [f"L{i}" for i in range(num_locations)]
    coords = {loc: (rng.random(), rng.random()) for loc in locations}
    return locations, coords


def make_symmetric_travel_times(
    locations: List[str],
    coords: Dict[str, Tuple[float, float]],
    *,
    base_minutes: int = 5,
    minutes_per_unit: int = 100,
    noise: float = 0.10,
    seed: int = 0,
) -> Dict[Tuple[str, str], int]:
    """
    Build a COMPLETE symmetric travel-time matrix in minutes.

    For each unordered pair {a,b}:
      time(a,b) = base_minutes + minutes_per_unit * euclidean_distance(a,b) + noise
    Then enforce symmetry:
      time(a,b) == time(b,a)

    Returns a dict travel_times[(locA, locB)] -> minutes.
    """
    rng = random.Random(seed)

    def euclid(a: str, b: str) -> float:
        ax, ay = coords[a]
        bx, by = coords[b]
        return math.hypot(ax - bx, ay - by)

    tt: Dict[Tuple[str, str], int] = {}

    for i, a in enumerate(locations):
        tt[(a, a)] = 0
        for b in locations[i + 1:]:
            d = euclid(a, b)
            t = base_minutes + minutes_per_unit * d
            #t *= (1.0 + rng.uniform(-noise, noise))  # random variation
            t = max(1, int(round(t)))

            # symmetry enforced
            tt[(a, b)] = t
            tt[(b, a)] = t

    return tt


# ============================================================
# 2) TRAVEL-FEASIBLE RANDOM BLOCKED SCHEDULES (MANDATORY EVENTS)
# ============================================================

def generate_travel_feasible_blocks_for_barrister(
    *,
    home: str,
    day_start: int,
    day_end: int,
    locations: List[str],
    travel_times: Dict[Tuple[str, str], int],
    rng: random.Random,
    blocked_frac: float,
    constrainedness: float,
    time_step: int = 5,
    max_tries: int = 300,
):
    """
    Create a barrister's blocked schedule (mandatory events) with RANDOM LOCATIONS
    while guaranteeing the entire chain is travel-feasible:

      HOME@day_start -> block1 -> block2 -> ... -> blockK -> HOME@day_end

    Returns blocks like:
      [{"start_time": s, "end_time": e, "location": "L3"}, ...]

    Strategy:
      A) sample disjoint time intervals (non-overlapping)
      B) assign locations sequentially with travel feasibility checks (+ light lookahead)
      C) final strict verification of the full chain
    """

    def round_to_step(t: int) -> int:
        return int(time_step * round(t / time_step))

    def T(a: str, b: str) -> int:
        # with symmetric matrix, always exists
        return travel_times[(a, b)]

    day_len = day_end - day_start
    target_blocked = int(round(blocked_frac * day_len))

    # More constrainedness => more blocks => typically harder chaining
    max_blocks = 1 + int(round(4 * constrainedness))
    num_blocks = rng.randint(0, max_blocks)

    # Split target blocked minutes into random durations
    durations: List[int] = []
    remaining = target_blocked
    for _ in range(num_blocks):
        if remaining <= 15:
            break
        dur = rng.randint(15, min(120, remaining))
        remaining -= dur
        durations.append(dur)

    # ---------- Stage A: sample disjoint time intervals ----------
    for _ in range(max_tries):
        intervals: List[Tuple[int, int]] = []

        for dur in durations:
            placed = False
            for __ in range(80):
                s = rng.randint(day_start, day_end - dur)
                s = round_to_step(s)
                e = s + dur

                # overlap check against already placed intervals
                if any(not (e <= s2 or e2 <= s) for (s2, e2) in intervals):
                    continue

                intervals.append((s, e))
                placed = True
                break

            if not placed:
                break

        if len(intervals) != len(durations):
            continue

        intervals.sort()
        blocks = [{"start_time": s, "end_time": e, "location": None} for (s, e) in intervals]

        # ---------- Stage B: assign locations sequentially ----------
        ok = True

        for i, blk in enumerate(blocks):
            s, e = blk["start_time"], blk["end_time"]

            # predecessor anchor
            if i == 0:
                prev_loc, prev_end = home, day_start
            else:
                prev_loc, prev_end = blocks[i - 1]["location"], blocks[i - 1]["end_time"]

            # next anchor time (location unknown until we choose it)
            if i == len(blocks) - 1:
                next_start = day_end
            else:
                next_start = blocks[i + 1]["start_time"]

            candidates = locations[:]
            rng.shuffle(candidates)

            chosen = None
            for loc in candidates:
                # must be able to travel from previous anchor to this block
                if prev_end + T(prev_loc, loc) > s:
                    continue

                # if last block, must be able to return home by day_end
                if i == len(blocks) - 1 and e + T(loc, home) > day_end:
                    continue

                # light lookahead: if there is a next block, ensure *some* location can work next
                if i < len(blocks) - 1:
                    feasible_next_exists = False
                    for loc2 in candidates:
                        if e + T(loc, loc2) <= next_start:
                            feasible_next_exists = True
                            break
                    if not feasible_next_exists:
                        continue

                chosen = loc
                break

            if chosen is None:
                ok = False
                break

            blk["location"] = chosen

        if not ok:
            continue

        # ---------- Stage C: final strict chain verification ----------
        prev_loc, prev_end = home, day_start
        for blk in blocks:
            if prev_end + T(prev_loc, blk["location"]) > blk["start_time"]:
                ok = False
                break
            prev_loc, prev_end = blk["location"], blk["end_time"]

        if ok and (prev_end + T(prev_loc, home) <= day_end):
            return blocks

    # If we can't find a feasible random-location schedule, return empty schedule.
    # (You can raise instead if you prefer.)
    return []


# ============================================================
# 3) FULL INSTANCE GENERATOR (BARRISTERS + FEASIBLE MANDATORY SCHEDULES)
# ============================================================

fields = ["Criminal", "Fraud", "Family" "Civil", "Commercial", "Employment", "Housing", "Immigration",
            "Personal Injury", "Wills", "Property", "Tax", "Intellectual Property"]
       

def generate_barristers_travel_times(
    num_barristers: int = 20,
    num_locations: int = 12,
    seed: int = 0,
    day_start: int = 9 * 60,
    day_end: int = 17 * 60,
    time_step: int = 5,
    constrainedness: float = 0.5,    # 0 easy -> 1 tighter (more blocks, longer travel)
    phase: str = "phase_transition", # "easy" | "phase_transition" | "hard"
):
    """
    Generates:
      - barristers (with travel-feasible mandatory schedules)
      - symmetric travel_times
      - locations list

    This does NOT generate cases; it's the "base-only" generator focused on:
      * symmetric travel matrix
      * guaranteed feasible barrister schedules (HOME->blocks->HOME)

    You can build your cases on top of this.
    """
    rng = random.Random(seed)

    # --- locations + coordinates ---
    locations, coords = make_locations(num_locations, seed=seed + 101)

    # --- travel times (symmetric) ---
    minutes_per_unit = int(round(60 + 90 * max(0.0, min(1.0, constrainedness))))  # ~60..150
    travel_times = make_symmetric_travel_times(
        locations,
        coords,
        base_minutes=6,
        minutes_per_unit=minutes_per_unit,
        noise=0.10,
        seed=seed + 202,
    )

    # --- how much of the day is blocked (depends on phase + constrainedness) ---
    if phase == "easy":
        blocked_frac = 0.05 + 0.20 * constrainedness
    elif phase == "hard":
        blocked_frac = 0.20 + 0.45 * constrainedness
    else:  # phase_transition
        blocked_frac = 0.10 + 0.35 * constrainedness

    blocked_frac = max(0.0, min(0.9, blocked_frac))  # clamp

    # --- seniority sampler ---
    def sample_seniority() -> int:
        # Adjust distribution if you want more/less high seniority barristers
        if constrainedness < 0.35:
            return rng.choices([1, 2, 3], weights=[0.25, 0.30, 0.45])[0]
        elif constrainedness < 0.70:
            return rng.choices([1, 2, 3], weights=[0.35, 0.35, 0.30])[0]
        else:
            return rng.choices([1, 2, 3], weights=[0.45, 0.35, 0.20])[0]
        
    def sample_experience():
        return rng.choices(range(30))[0]

    def sample_expertise():
        num = rng.choices([1, 2, 3], weights=[0.3, 0.4, 0.3])[0] # will have between 1 - 3 expertises 
        expertises = random.sample(fields, num)  
        return expertises
    
    def sample_winrate():
        return round(((random.random() + random.random() + random.random()) / 3), 2)

    # --- build barristers + mandatory schedules ---
    barristers: List[dict] = []
    for i in range(num_barristers):
        home = rng.choice(locations)
        b = {
            "name": f"B{i}",
            "home": home,
            "day_start": day_start,
            "day_end": day_end,
            "seniority": sample_seniority(),
            "experience": sample_experience(),
            "expertise": sample_expertise(),
            "winrate": sample_winrate(),
            "schedule": []
        }

        # generate a travel-feasible random-location blocked schedule
        b["schedule"] = generate_travel_feasible_blocks_for_barrister(
            home=home,
            day_start=day_start,
            day_end=day_end,
            locations=locations,
            travel_times=travel_times,
            rng=rng,
            blocked_frac=blocked_frac,
            constrainedness=constrainedness,
            time_step=time_step,
            max_tries=400,  # a bit higher for reliability
        )

        barristers.append(b)

    return barristers, travel_times, locations


#4 CASES

def estimate_available_minutes(barristers: List[dict]) -> int:
    """
    Rough capacity estimate ignoring travel:
    total working minutes - blocked minutes across all barristers.
    """
    total = 0
    for b in barristers:
        day_len = b["day_end"] - b["day_start"]
        blocked = sum(blk["end_time"] - blk["start_time"] for blk in b.get("schedule", []))
        total += max(0, day_len - blocked)
    return total


def suggest_num_cases(
    barristers: List[dict],
    target_load: float,
    constrainedness: float = 0.5,
) -> int:
    """
    target_load = desired ratio of total case minutes / available barrister minutes.
    Example:
      0.4 easy
      0.7 moderate
      0.9 hard
      1.1 very hard / likely unassigneds
    """
    avail = estimate_available_minutes(barristers)
    target_case_minutes = target_load * avail
    avg_case_duration = 30 + (constrainedness * 30)
    return max(1, int(round(target_case_minutes / avg_case_duration)))


def generate_cases(
    barristers: List[dict],
    locations: List[str],
    num_cases: int,
    seed: int = 0,
    constrainedness: float = 0.5,  # 0 easy -> 1 hard
    phase: str = "phase_transition",  # "easy" | "phase_transition" | "hard"
    time_step: int = 5,
) -> Tuple[List[dict], Dict[Tuple[str, str], int]]:
    """
    Generates random cases (not guaranteed fully assignable).
    Constrainedness controls:
      - duration lengths
      - time clustering
      - seniority pressure
    """
    rng = random.Random(seed)
    constrainedness = max(0.0, min(1.0, constrainedness))

    day_start = min(b["day_start"] for b in barristers)
    day_end = max(b["day_end"] for b in barristers)

    def round_to_step(t: int) -> int:
        return int(time_step * round(t / time_step))

    # ---------------------------
    # Hardness controls
    # ---------------------------
    # More constrained => longer durations
    def sample_duration() -> int:
        if constrainedness < 0.35:
            return rng.choice([20, 25, 30, 35, 40, 45])
        elif constrainedness < 0.70:
            return rng.choice([25, 30, 35, 40, 45, 60])
        else:
            return rng.choice([30, 40, 45, 60, 75, 90])

    # More constrained => more higher-seniority cases
    def sample_case_seniority() -> int:
        if constrainedness < 0.35:
            return rng.choices([1, 2, 3], weights=[0.75, 0.22, 0.03])[0]
        elif constrainedness < 0.70:
            return rng.choices([1, 2, 3], weights=[0.55, 0.30, 0.15])[0]
        else:
            return rng.choices([1, 2, 3], weights=[0.35, 0.40, 0.25])[0]

    # Time clustering: hard instances cluster more
    if phase == "easy":
        cluster_strength = 0.20 + 0.30 * constrainedness
    elif phase == "hard":
        cluster_strength = 0.60 + 0.30 * constrainedness
    else:  # phase_transition
        cluster_strength = 0.40 + 0.35 * constrainedness

    # Peak times (e.g. common court hearing slots)
    peak_centers = [
        day_start + int(0.20 * (day_end - day_start)),
        day_start + int(0.45 * (day_end - day_start)),
        day_start + int(0.70 * (day_end - day_start)),
    ]

    def sample_start_time() -> int:
        if rng.random() < cluster_strength:
            center = rng.choice(peak_centers)
            spread = int((1.0 - constrainedness) * 90 + 20)  # minutes
            t = center + rng.randint(-spread, spread)
        else:
            t = rng.randint(day_start, day_end)
        return round_to_step(max(day_start, min(day_end, t)))

    def sample_case_type() -> str:
        return rng.choice(fields)

    def sample_severity() -> bool:
        # You can tune this too if you want "harder" quality-matching problems
        return rng.choices([True, False], weights=[0.35, 0.65])[0]

    # ---------------------------
    # Generate cases
    # ---------------------------
    cases: List[dict] = []
    for i in range(num_cases):
        c = {
            "name": f"C{i}",
            "time": sample_start_time(),
            "duration": sample_duration(),
            "location": rng.choice(locations),
            "seniority": sample_case_seniority(),
            "type": sample_case_type(),
            "severe": sample_severity(),
        }
        cases.append(c)

    cases.sort(key=lambda x: x["time"])

    return cases

def generate_test_case(num_barristers, num_locations, constrainedness, target_load, phase):

    barristers, travel_times, locations = generate_barristers_travel_times(num_barristers, num_locations, constrainedness=constrainedness, phase=phase)
    print(barristers)
    print(travel_times)
    print(locations)
    num_cases = suggest_num_cases(barristers, target_load, constrainedness=constrainedness)
    print(num_cases)
    cases = generate_cases(barristers, locations, num_cases, constrainedness=constrainedness, phase=phase)
    print(cases)

    return barristers, cases, travel_times
  