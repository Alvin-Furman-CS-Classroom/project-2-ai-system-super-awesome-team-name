import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module4.meal_suggestion_planner import (
    MealSuggestionPlanner,
    _Node,
    infer_food_category,
    infer_grain_starch_subfamily,
    meal_has_duplicate_replacement_across_distinct_foods,
    suggestion_count_for_category,
)


class FakeKB:
    def __init__(self):
        self._foods = {
            "white rice": {"glycemic_index": 90.0, "fiber": 0.8, "glycemic_load": 40.0},
            "brown rice": {"glycemic_index": 50.0, "fiber": 2.2, "glycemic_load": 18.0},
            "wild rice": {"glycemic_index": 57.0, "fiber": 2.5, "glycemic_load": 19.0},
            "basmati rice": {"glycemic_index": 58.0, "fiber": 1.8, "glycemic_load": 20.0},
            "quinoa": {"glycemic_index": 53.0, "fiber": 2.8, "glycemic_load": 19.0},
            "white bread": {"glycemic_index": 70.0, "fiber": 1.0, "glycemic_load": 30.0},
            "broccoli": {"glycemic_index": 15.0, "fiber": 3.0, "glycemic_load": 2.0},
            "lentils": {"glycemic_index": 30.0, "fiber": 7.0, "glycemic_load": 10.0},
            "chicken breast": {"glycemic_index": 0.0, "fiber": 0.0, "glycemic_load": 0.0},
        }

    def list_all_foods(self):
        return list(self._foods.keys())

    def get_nutrition_features(self, food_name, serving_size="100g"):
        row = self._foods[food_name]
        sl = serving_size.strip().lower()
        grams = 100.0
        if "serving" not in sl and sl.endswith("g"):
            grams = float(sl[:-1].strip())
        scale = grams / 100.0
        return {
            "glycemic_index": row["glycemic_index"],
            "fiber": row["fiber"] * scale,
            "glycemic_load": row["glycemic_load"] * scale,
            "serving_size_grams": grams,
        }


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


class GLThresholdAnalyzer:
    """Classifies meals by summed scaled glycemic load (for FakeKB tests)."""

    def __init__(self, kb):
        self._kb = kb

    def analyze_meal(self, meal_items):
        total_gl = 0.0
        for m in meal_items:
            feats = self._kb.get_nutrition_features(m["food_name"], m["serving_size"])
            total_gl += float(feats["glycemic_load"])
        if total_gl > 50:
            return {"meal_risk_category": "high", "risk_score": 95.0}
        if total_gl > 20:
            return {"meal_risk_category": "medium", "risk_score": 55.0}
        return {"meal_risk_category": "low", "risk_score": 25.0}


class AddedSwapOnlyAnalyzer:
    """
    Fake rule:
      - medium unless "bean" is present
      - low only when "bean" is present

    Because "bean" is only introduced in this test by swapping the *added*
    legume item, the planner should not be able to reach the goal when
    swaps are restricted to the original meal items.
    """

    def analyze_meal(self, meal_items):
        names = [m["food_name"] for m in meal_items]
        if "bean" in names:
            return {"meal_risk_category": "low", "risk_score": 25.0}
        return {"meal_risk_category": "medium", "risk_score": 55.0}


class TestMealSuggestionPlanner(unittest.TestCase):
    def test_category_inference_and_counts(self):
        self.assertEqual(infer_food_category("white rice"), "grain_starch")
        self.assertEqual(infer_food_category("brown rice"), "grain_starch")
        self.assertEqual(infer_food_category("broccoli"), "vegetable")
        # "oat" must not match inside "goat" (substring bug).
        self.assertEqual(infer_food_category("goat cheese"), "dairy")
        self.assertEqual(infer_food_category("rice vinegar"), "fat_condiment")
        self.assertEqual(infer_food_category("rice milk"), "beverage")
        self.assertEqual(infer_food_category("wild rice tempeh"), "protein")

    def test_grain_starch_subfamily_rice_not_pasta(self):
        self.assertIsNone(infer_grain_starch_subfamily("rice milk"))
        self.assertEqual(infer_grain_starch_subfamily("white rice steamed"), "rice")
        self.assertEqual(infer_grain_starch_subfamily("pasta salad no dressing"), "pasta")
        self.assertEqual(infer_grain_starch_subfamily("white bread fresh"), "bread")
        self.assertEqual(infer_grain_starch_subfamily("potato salad with dressing"), "potato")
        self.assertIsNone(infer_grain_starch_subfamily("broccoli"))

    def test_duplicate_replacement_detection(self):
        start = (("white rice", "100g"), ("white bread", "100g"))
        bad = (("brown rice", "100g"), ("brown rice", "100g"))
        good = (("brown rice", "100g"), ("whole wheat bread", "100g"))
        self.assertTrue(
            meal_has_duplicate_replacement_across_distinct_foods(start, bad, 2)
        )
        self.assertFalse(
            meal_has_duplicate_replacement_across_distinct_foods(start, good, 2)
        )
        # Two identical originals may both change to the same target.
        start2 = (("white rice", "100g"), ("white rice", "100g"))
        ok_dup = (("brown rice", "100g"), ("brown rice", "100g"))
        self.assertFalse(
            meal_has_duplicate_replacement_across_distinct_foods(start2, ok_dup, 2)
        )
        self.assertEqual(suggestion_count_for_category("high"), 5)
        self.assertEqual(suggestion_count_for_category("medium"), 3)
        self.assertEqual(suggestion_count_for_category("caution"), 3)
        self.assertEqual(suggestion_count_for_category("low"), 0)

    def test_expand_includes_portion_reduction(self):
        planner = MealSuggestionPlanner(FakeKB(), FakeAnalyzer(), max_edits=3)
        planner._original_count = 1
        planner._start_meal = (("white rice", "200g"),)
        node = _Node(meal=(("white rice", "200g"),), actions=tuple(), edits_count=0)
        children = planner._expand(node)
        reduce_nodes = [n for n in children if n.actions and "Reduce portion" in n.actions[0]]
        self.assertGreaterEqual(len(reduce_nodes), 1)
        joined = " ".join(n.actions[0] for n in reduce_nodes)
        self.assertIn("150g", joined)
        self.assertIn("100g", joined)
        self.assertIn("50g", joined)

    def test_portion_reduction_can_reach_goal(self):
        class RiceOnlyKB(FakeKB):
            def __init__(self):
                self._foods = {
                    "white rice": {
                        "glycemic_index": 90.0,
                        "fiber": 0.8,
                        "glycemic_load": 40.0,
                    },
                }

        kb = RiceOnlyKB()
        planner = MealSuggestionPlanner(
            kb, GLThresholdAnalyzer(kb), max_edits=2, max_expansions=120
        )
        result = planner.generate_suggestions(
            [{"food_name": "white rice", "serving_size": "200g"}],
            original_category="high",
            algorithm="astar",
        )
        self.assertEqual(result["status"], "suggestions_found")
        actions_blob = " ".join(" ".join(s["actions"]) for s in result["suggestions"])
        self.assertIn("Reduce portion", actions_blob)

    def test_starch_swaps_stay_within_subfamily(self):
        class KB(FakeKB):
            def __init__(self):
                super().__init__()
                self._foods["pasta salad no dressing"] = {
                    "glycemic_index": 25.0,
                    "fiber": 3.0,
                    "glycemic_load": 10.0,
                }

        planner = MealSuggestionPlanner(KB(), FakeAnalyzer(), max_edits=1, max_expansions=5)
        cands = planner._swap_candidates("white rice")
        self.assertIn("brown rice", cands)
        self.assertNotIn("pasta salad no dressing", cands)

    def test_same_category_swaps_are_used(self):
        planner = MealSuggestionPlanner(
            FakeKB(), FakeAnalyzer(), max_edits=2, max_expansions=80
        )
        suggestions = planner.generate_suggestions(
            [{"food_name": "white rice", "serving_size": "100g"}],
            original_category="medium",
            algorithm="astar",
        )["suggestions"]
        self.assertEqual(len(suggestions), 3)
        for s in suggestions:
            self.assertEqual(s["resulting_category"], "low")
        joined_actions = " ".join(" ".join(s["actions"]) for s in suggestions)
        self.assertIn("brown rice", joined_actions)
        self.assertNotIn("white bread", joined_actions)

    def test_high_risk_requests_up_to_five_suggestions(self):
        planner = MealSuggestionPlanner(
            FakeKB(), FakeAnalyzer(), max_edits=3, max_expansions=120
        )
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
            self.assertIn(s["resulting_category"], ("medium", "low"))

    def test_diversity_filters_prep_variants(self):
        class KB3(FakeKB):
            def __init__(self):
                super().__init__()
                self._foods["brown rice boiled"] = {
                    "glycemic_index": 50.0,
                    "fiber": 2.2,
                    "glycemic_load": 18.0,
                }
                self._foods["brown rice steamed"] = {
                    "glycemic_index": 50.0,
                    "fiber": 2.2,
                    "glycemic_load": 18.0,
                }

        planner = MealSuggestionPlanner(
            KB3(), FakeAnalyzer(), max_edits=2, max_expansions=120
        )
        result = planner.generate_suggestions(
            [{"food_name": "white rice", "serving_size": "100g"}],
            original_category="medium",
            algorithm="astar",
            top_k=2,
        )
        self.assertEqual(result["status"], "suggestions_found")
        actions_text = " ".join(" ".join(s["actions"]) for s in result["suggestions"])
        self.assertFalse(
            "brown rice boiled" in actions_text and "brown rice steamed" in actions_text
        )

    def test_status_low_risk_no_suggestions_needed(self):
        planner = MealSuggestionPlanner(
            FakeKB(), FakeAnalyzer(), max_edits=2, max_expansions=40
        )
        result = planner.generate_suggestions(
            [{"food_name": "brown rice", "serving_size": "100g"}],
            original_category="low",
            algorithm="astar",
        )
        self.assertEqual(result["status"], "low_risk_no_suggestions_needed")
        self.assertEqual(result["suggestions"], [])

    def test_status_no_suggestions_found_when_goal_not_reached(self):
        planner = MealSuggestionPlanner(
            FakeKB(), NeverGoalAnalyzer(), max_edits=1, max_expansions=10
        )
        result = planner.generate_suggestions(
            [{"food_name": "white rice", "serving_size": "100g"}],
            original_category="high",
            algorithm="ucs",
        )
        self.assertEqual(result["status"], "no_suggestions_found")
        self.assertEqual(result["suggestions"], [])

    def test_swap_cannot_replace_added_items(self):
        class KB2(FakeKB):
            def __init__(self):
                super().__init__()
                self._foods = {
                    "chicken breast": {
                        "glycemic_index": 0.0,
                        "fiber": 0.0,
                        "glycemic_load": 0.0,
                    },
                    "lentils": {
                        "glycemic_index": 30.0,
                        "fiber": 7.0,
                        "glycemic_load": 10.0,
                    },
                    "bean": {
                        "glycemic_index": 80.0,
                        "fiber": 0.2,
                        "glycemic_load": 25.0,
                    },
                }

        planner = MealSuggestionPlanner(
            KB2(), AddedSwapOnlyAnalyzer(), max_edits=2, max_expansions=80
        )
        result = planner.generate_suggestions(
            [{"food_name": "chicken breast", "serving_size": "100g"}],
            original_category="medium",
            algorithm="astar",
        )
        self.assertEqual(result["status"], "no_suggestions_found")
        self.assertEqual(result["suggestions"], [])


if __name__ == "__main__":
    unittest.main()
