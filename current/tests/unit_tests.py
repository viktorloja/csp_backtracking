import unittest
import sys
import os

# Ensure we can import from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processing.run_algorithms import calculate_costs_optimal, calculate_costs_balanced
from algorithms.greedy import build_base_timelines, Event, greedy
from algorithms.backtrack_naive import case_fits, case_insert_cost, travel, calculate_initial_cost, branch_and_bound_naive, define_inputs as define_inputs_naive
from algorithms.backtrack_optimized import branch_and_bound_optimized, define_inputs as define_inputs_opt
from algorithms.local_search import local_search

class TestCostCalculations(unittest.TestCase):
    def setUp(self):
        self.barristers = [
            {
                "name": "B1",
                "expertise": ["Criminal"],
                "experience": 5,
                "winrate": 0.8,
                "seniority": 2
            },
            {
                "name": "B2",
                "expertise": ["Civil"],
                "experience": 1,
                "winrate": 0.5,
                "seniority": 1
            }
        ]
        self.cases = [
            {
                "name": "C1",
                "type": "Criminal",
                "severe": True,
                "time": 600,
                "duration": 60,
                "location": "L1"
            },
            {
                "name": "C2",
                "type": "Family",
                "severe": False,
                "time": 800,
                "duration": 60,
                "location": "L1"
            }
        ]

    def test_calculate_costs_optimal(self):
        costs = calculate_costs_optimal(self.cases, self.barristers)
        
        # B1 on C1 (Criminal match): 
        # Base 600 - 200 (expertise) - min(200, 5*10=50) - 200*0.8 (160) 
        # = 600 - 200 - 50 - 160 = 190
        self.assertAlmostEqual(costs[("C1", "B1")], 190)

        # B2 on C1 (No match):
        # Base 600 - min(200, 1*10=10) - 200*0.5 (100)
        # = 600 - 10 - 100 = 490
        self.assertAlmostEqual(costs[("C1", "B2")], 490)

    def test_calculate_costs_balanced(self):
        costs = calculate_costs_balanced(self.cases, self.barristers)
        
        # B2 (exp 1) on C2 (Not severe): Training opportunity
        # Base 700
        # Expertise: No match (Civil != Family) -> 0 reduction
        # Training: Not severe + exp < 3 -> -300
        # Winrate: -200 * 0.5 = -100
        # Total: 700 - 300 - 100 = 300
        self.assertEqual(costs[("C2", "B2")], 300)

class TestTimelineFunctions(unittest.TestCase):
    def setUp(self):
        self.barristers = [{
            "name": "B1",
            "home": "H",
            "day_start": 540, # 09:00
            "day_end": 1020,  # 17:00
            "schedule": [
                {"start_time": 720, "end_time": 780, "location": "L1"} # 12:00-13:00
            ]
        }]
        
    def test_build_base_timelines(self):
        base, starts = build_base_timelines(self.barristers)
        timeline = base["B1"]
        
        self.assertEqual(len(timeline), 3)
        self.assertEqual(timeline[0].location, "H")
        self.assertEqual(timeline[0].name, "HOME_START")
        
        self.assertEqual(timeline[1].start, 720)
        self.assertEqual(timeline[1].location, "L1")
        
        self.assertEqual(timeline[2].location, "H")
        self.assertEqual(timeline[2].name, "HOME_END")
        
        self.assertEqual(starts["B1"], [540, 720, 1020])

class TestBacktrackHelpers(unittest.TestCase):
    def setUp(self):
        # Timeline: Home(540) -> Block(720-780 @ L1) -> Home(1020)
        self.timeline = [
            Event(540, 540, "H", "HOME_START"),
            Event(720, 780, "L1", "BLOCKED"),
            Event(1020, 1020, "H", "HOME_END")
        ]
        self.starts = [540, 720, 1020]
        self.travel_times = {
            ("H", "L1"): 30,
            ("L1", "H"): 30,
            ("L1", "L2"): 20,
            ("H", "L2"): 40,
            ("L2", "L1"): 20,
            ("L2", "H"): 40
        }
        
    def test_case_fits_success(self):
        # Case at 600 (10:00), duration 60, loc L1
        # Prev: Home(540). Travel H->L1 = 30. Arrival 570. Fits before 600.
        # Next: Block(720). Travel L1->L1 = 0 (assumed). End 660. Fits before 720.
        case = {"time": 600, "duration": 60, "location": "L1"}
        fits = case_fits(case, self.timeline, self.starts, self.travel_times)
        self.assertTrue(fits)

    def test_case_fits_fail_travel(self):
        # Case at 550, duration 60, loc L1
        # Prev: Home(540). Travel H->L1 = 30. Arrival 570. 
        # 570 > 550, so should fail.
        case = {"time": 550, "duration": 60, "location": "L1"}
        fits = case_fits(case, self.timeline, self.starts, self.travel_times)
        self.assertFalse(fits)

    def test_case_insert_cost(self):
        # Case at 600, loc L2.
        # Prev: H. Next: L1.
        # Old: H->L1 (30).
        # New: H->L2 (40) + L2->L1 (20). Total 60.
        # Delta = 60 - 30 = 30.
        case = {"time": 600, "duration": 60, "location": "L2"}
        delta, idx = case_insert_cost(case, self.timeline, self.starts, self.travel_times)
        
        self.assertEqual(delta, 30)
        self.assertEqual(idx, 1) # Insert before index 1 (Block)

class TestTravelHelpers(unittest.TestCase):
    def setUp(self):
        self.travel_times = {
            ("A", "B"): 10,
            ("B", "A"): 10,
            ("A", "C"): 20
        }

    def test_travel_same_location(self):
        self.assertEqual(travel(self.travel_times, "A", "A"), 0)

    def test_travel_lookup(self):
        self.assertEqual(travel(self.travel_times, "A", "B"), 10)
        self.assertEqual(travel(self.travel_times, "A", "C"), 20)

    def test_travel_missing(self):
        self.assertIsNone(travel(self.travel_times, "B", "C"))

    def test_calculate_initial_cost(self):
        # Setup a timeline for one barrister
        # Home(A) -> Block(B) -> Home(A)
        # Cost: A->B (10) + B->A (10) = 20
        timelines = {
            "B1": [
                Event(0, 0, "A", "HOME_START"),
                Event(100, 200, "B", "BLOCKED"),
                Event(300, 300, "A", "HOME_END")
            ]
        }
        cost = calculate_initial_cost(timelines, self.travel_times)
        self.assertEqual(cost, 20)

class TestConstraintGeneration(unittest.TestCase):
    def setUp(self):
        self.barristers = [{
            "name": "B1", "home": "A", "day_start": 540, "day_end": 1020, 
            "seniority": 1, "schedule": []
        }]
        self.travel_times = {("A", "A"): 0}

    def test_overlapping_cases(self):
        # C1: 10:00-11:00, C2: 10:30-11:30 at same location
        cases = [
            {"name": "C1", "time": 600, "duration": 60, "location": "A", "seniority": 1},
            {"name": "C2", "time": 630, "duration": 60, "location": "A", "seniority": 1}
        ]
        domains, constraints, _, _ = define_inputs_naive(cases, self.barristers, self.travel_times)
        
        # Should be constrained because they overlap
        self.assertTrue(("C1", "C2") in constraints or ("C2", "C1") in constraints)

    def test_non_overlapping_cases(self):
        # C1: 10:00-11:00, C2: 11:00-12:00 at same location (travel 0)
        cases = [
            {"name": "C1", "time": 600, "duration": 60, "location": "A", "seniority": 1},
            {"name": "C2", "time": 660, "duration": 60, "location": "A", "seniority": 1}
        ]
        domains, constraints, _, _ = define_inputs_naive(cases, self.barristers, self.travel_times)
        
        # Should NOT be constrained (C1 ends at 660, C2 starts at 660)
        self.assertFalse(("C1", "C2") in constraints or ("C2", "C1") in constraints)

class TestFullAlgorithms(unittest.TestCase):
    def setUp(self):
        self.barristers = [{
            "name": "B1", "home": "A", "day_start": 540, "day_end": 1020, 
            "seniority": 2, "schedule": [], "expertise": [], "experience": 5, "winrate": 0.5
        }]
        self.cases = [{
            "name": "C1", "time": 600, "duration": 60, "location": "B", "seniority": 1,
            "type": "Civil", "severe": False
        }]
        self.travel_times = {
            ("A", "B"): 10, ("B", "A"): 10,
            ("A", "A"): 0, ("B", "B"): 0
        }
        self.case_costs = {("C1", "B1"): 10, ("C1", "UNASSIGNED"): 1000}

    def test_greedy_assigns(self):
        assignment, _, _, _ = greedy(
            self.cases, self.barristers, self.travel_times, self.case_costs, {}
        )
        self.assertEqual(assignment["C1"], "B1")

    def test_greedy_seniority_check(self):
        self.cases[0]["seniority"] = 3 # Higher than B1 (2)
        assignment, _, _, _ = greedy(
            self.cases, self.barristers, self.travel_times, self.case_costs, {}
        )
        self.assertEqual(assignment["C1"], "UNASSIGNED")

    def test_backtrack_naive_assigns(self):
        domains, constraints, timelines, starts = define_inputs_naive(self.cases, self.barristers, self.travel_times)
        sol, cost, _ = branch_and_bound_naive(
            self.cases, timelines, starts, self.travel_times, self.case_costs, domains, constraints
        )
        self.assertEqual(sol["C1"], "B1")

    def test_backtrack_optimized_assigns(self):
        domains, constraints, timelines, starts = define_inputs_opt(self.cases, self.barristers, self.travel_times)
        sol, cost, _ = branch_and_bound_optimized(
            self.cases, timelines, starts, self.travel_times, self.case_costs, domains, constraints
        )
        self.assertEqual(sol["C1"], "B1")

    def test_backtracking_returns_schedule_with_assigned_case(self):
        domains, constraints, timelines, starts = define_inputs_naive(self.cases, self.barristers, self.travel_times)
        sol, _, best_timelines = branch_and_bound_naive(
            self.cases, timelines, starts, self.travel_times, self.case_costs, domains, constraints
        )

        assigned_events = [event.name for event in best_timelines["B1"]]
        self.assertEqual(sol["C1"], "B1")
        self.assertIn("C1", assigned_events)


class TestLocalSearchRegressions(unittest.TestCase):
    def test_local_search_does_not_swap_into_seniority_violation(self):
        barristers = [
            {"name": "B1", "home": "A", "day_start": 0, "day_end": 200, "seniority": 1},
            {"name": "B2", "home": "B", "day_start": 0, "day_end": 200, "seniority": 3},
        ]
        cases = [
            {"name": "C1", "time": 10, "duration": 10, "location": "B", "seniority": 1},
            {"name": "C2", "time": 30, "duration": 10, "location": "A", "seniority": 3},
        ]
        assignments = {"C1": "B1", "C2": "B2"}
        timelines = {
            "B1": [
                Event(0, 0, "A", "HOME_START"),
                Event(10, 20, "B", "C1"),
                Event(200, 200, "A", "HOME_END"),
            ],
            "B2": [
                Event(0, 0, "B", "HOME_START"),
                Event(30, 40, "A", "C2"),
                Event(200, 200, "B", "HOME_END"),
            ],
        }
        timeline_starts = {"B1": [0, 10, 200], "B2": [0, 30, 200]}
        travel_times = {
            ("A", "A"): 0,
            ("B", "B"): 0,
            ("A", "B"): 100,
            ("B", "A"): 100,
        }
        case_costs = {
            ("C1", "B1"): 0,
            ("C1", "B2"): -250,
            ("C2", "B1"): -250,
            ("C2", "B2"): 0,
        }

        new_assignments, _, new_score = local_search(
            barristers,
            cases,
            assignments,
            timelines,
            timeline_starts,
            case_costs,
            travel_times,
            current_score=400,
        )

        self.assertEqual(new_assignments["C1"], "B1")
        self.assertEqual(new_assignments["C2"], "B2")
        self.assertEqual(new_score, 400)

if __name__ == '__main__':
    unittest.main()
