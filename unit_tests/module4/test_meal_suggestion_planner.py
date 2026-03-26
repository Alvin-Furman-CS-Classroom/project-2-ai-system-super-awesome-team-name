import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module4.meal_suggestion_planner import (
    MealSuggestionPlanner,
    infer_food_category,
    suggestion_count_for_category,
)


class FakeKB:
    def __init__(self):
        self._foods = {
            "white rice": {"glycemic_index": 90.0, "fiber": 0.8},
            "brown rice": {"glycemic_index": 50.0, "fiber": 2.2},
            "quinoa": {"glycemic_index": 53.0, "fiber": 2.8},
            "white bread": {"glycemic_index": 70.0, "fiber": 1.0},
            "broccoli": {"glycemic_index": 15.0, "fiber": 3.0},
            "lentils": {"glycemic_index": 30.0, "fiber": 7.0},
            "chicken breast": {"glycemic_index": 0.0, "fiber": 0.0},
        }

    def list_all_foods(self):
        return list(self._foods.keys())

    def get_nutrition_features(self, food_name, serving_size="100g"):
        row = self._foods[food_name]
        return {
            "glycemic_index": row["glycemic_index"],
            "fiber": row["fiber"],
        }


class FakeMatcher:
    def find_nearest_neighbors(self, query, top_k=5, offset=0):
        table = {
            "white rice": [
                ("brown rice", 0.9),
                ("quinoa", 0.8),
                ("white bread", 0.7),
            ],
            "white bread": [
                ("white rice", 0.9),
                ("brown rice", 0.8),
            ],
        }
        return table.get(query, [])[offset : offset + top_k]


class FakeAnalyzer:
    def analyze_meal(self, meal_items):
        names = [m["food_name"] for m in meal_items]
        if "white rice" in names and "white bread" in names:
            return {"meal_risk_category": "high", "risk_score": 92.0}
        if "white rice" in names:
            return {"meal_risk_category": "medium", "risk_score": 55.0}
        if "white bread" in names:
            return {"meal_risk_category": "medium", "risk_score": 52.0}
        return {"meal_risk_category": "low", "risk_score": 25.0}

class NeverGoalAnalyzer:
    def analyze_meal(self, meal_items):
        return {"meal_risk_category": "high", "risk_score": 95.0}


class TestMealSuggestionPlanner(unittest.TestCase):
    def test_category_inference_and_counts(self):
        self.assertEqual(infer_food_category("white rice"), "grain_starch")
        self.assertEqual(infer_food_category("brown rice"), "grain_starch")
        self.assertEqual(infer_food_category("broccoli"), "vegetable")
        self.assertEqual(suggestion_count_for_category("high"), 5)
        self.assertEqual(suggestion_count_for_category("medium"), 3)
        self.assertEqual(suggestion_count_for_category("caution"), 3)
        self.assertEqual(suggestion_count_for_category("low"), 0)

    def test_same_category_swaps_are_used(self):
        planner = MealSuggestionPlanner(FakeKB(), FakeAnalyzer(), matcher=FakeMatcher(), max_edits=2, max_expansions=80)
        suggestions = planner.generate_suggestions(
            [{"food_name": "white rice", "serving_size": "100g"}],
            original_category="medium",
            algorithm="astar",
        )["suggestions"]
        self.assertGreaterEqual(len(suggestions), 1)
        joined_actions = " ".join(" ".join(s["actions"]) for s in suggestions)
        self.assertIn("brown rice", joined_actions)
        self.assertNotIn("white bread", joined_actions)

    def test_high_risk_requests_up_to_five_suggestions(self):
        planner = MealSuggestionPlanner(FakeKB(), FakeAnalyzer(), matcher=FakeMatcher(), max_edits=3, max_expansions=120)
        result = planner.generate_suggestions(
            [
                {"food_name": "white rice", "serving_size": "100g"},
                {"food_name": "white bread", "serving_size": "100g"},
            ],
            original_category="high",
            algorithm="ucs",
        )
        self.assertLessEqual(len(result["suggestions"]), 5)
        for s in result["suggestions"]:
            self.assertLessEqual(len(s["actions"]), 5)

    def test_status_low_risk_no_suggestions_needed(self):
        planner = MealSuggestionPlanner(FakeKB(), FakeAnalyzer(), matcher=FakeMatcher(), max_edits=2, max_expansions=40)
        result = planner.generate_suggestions(
            [{"food_name": "brown rice", "serving_size": "100g"}],
            original_category="low",
            algorithm="astar",
        )
        self.assertEqual(result["status"], "low_risk_no_suggestions_needed")
        self.assertEqual(result["suggestions"], [])

    def test_status_no_suggestions_found_when_goal_not_reached(self):
        planner = MealSuggestionPlanner(FakeKB(), NeverGoalAnalyzer(), matcher=FakeMatcher(), max_edits=1, max_expansions=10)
        result = planner.generate_suggestions(
            [{"food_name": "white rice", "serving_size": "100g"}],
            original_category="high",
            algorithm="ucs",
        )
        self.assertEqual(result["status"], "no_suggestions_found")
        self.assertEqual(result["suggestions"], [])


if __name__ == "__main__":
    unittest.main()
