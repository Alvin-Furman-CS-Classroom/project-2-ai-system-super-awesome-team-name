import os
import sys
import tempfile
import unittest
from pathlib import Path

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module1.knowledge_base import NutritionKnowledgeBase
from src.module2.food_safety_engine import FoodSafetyEngine
from src.module3.meal_risk_analyzer import MealRiskAnalyzer
from src.module5.personalization_service import apply_feedback_and_persist
from src.module5.user_profile import default_profile, save_profile


class _SingleFoodKB(NutritionKnowledgeBase):
    """Small deterministic KB for cross-module threshold integration tests."""

    def __init__(self):
        super().__init__("src/module1/nutrition_data.csv")

    def list_all_foods(self):
        return ["test carb"]

    def get_nutrition_features(self, food_name: str, serving_size: str = "100g"):
        if food_name != "test carb":
            raise ValueError("Unknown food in test KB")
        return {
            "glycemic_index": 50.0,
            "glycemic_load": 9.8,
            "carbohydrates": 20.0,
            "fiber": 0.0,
            "protein": 0.0,
            "fat": 0.0,
            "processing_level": "processed",
            "serving_size_grams": 100.0,
        }


class TestModule5Integration(unittest.TestCase):
    def test_custom_thresholds_flow_into_module2_and_module3(self):
        kb = _SingleFoodKB()
        thresholds = {
            "safe_gl": 9.5,
            "caution_gl": 20.0,
            "safe_gi": 55.0,
            "caution_gi": 70.0,
        }
        engine = FoodSafetyEngine(kb, thresholds=thresholds)
        analyzer = MealRiskAnalyzer(
            knowledge_base=kb,
            food_safety_engine=engine,
            enable_effective_gl_adjustments=True,
            safe_gl_threshold=thresholds["safe_gl"],
            caution_gl_threshold=thresholds["caution_gl"],
        )

        food_eval = engine.evaluate_food("test carb", "100g")
        self.assertEqual(food_eval["safety_label"], "caution")

        meal_result = analyzer.analyze_meal_from_precomputed(
            meal_items=[{"food_name": "test carb", "serving_size": "100g"}],
            per_food_results=[
                {
                    "safety_label": food_eval["safety_label"],
                    "explanation": food_eval["explanation"],
                }
            ],  # type: ignore[arg-type]
            precomputed_totals={"total_gl": 9.8, "total_fiber_g": 0.0, "total_protein_g": 0.0},
        )
        self.assertEqual(meal_result["meal_risk_category"], "medium")

    def test_feedback_update_changes_next_module2_3_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.json"
            profile = default_profile()
            profile["rl_state"]["epsilon"] = 0.0
            state_key = "pred=low|score=0_39"
            profile["rl_state"]["q"][f"{state_key}|a=dec_safe_gl"] = 5.0
            save_profile(profile, profile_path)

            updated = apply_feedback_and_persist(
                predicted_category="low",
                predicted_score=10.0,
                outcome="no_spike",
                profile_path=profile_path,
            )
            self.assertEqual(updated["thresholds"]["safe_gl"], 9.5)

            kb = _SingleFoodKB()
            engine = FoodSafetyEngine(kb, thresholds=updated["thresholds"])
            analyzer = MealRiskAnalyzer(
                knowledge_base=kb,
                food_safety_engine=engine,
                enable_effective_gl_adjustments=True,
                safe_gl_threshold=updated["thresholds"]["safe_gl"],
                caution_gl_threshold=updated["thresholds"]["caution_gl"],
            )
            food_eval = engine.evaluate_food("test carb", "100g")
            self.assertEqual(food_eval["safety_label"], "caution")
            meal_result = analyzer.analyze_meal_from_precomputed(
                meal_items=[{"food_name": "test carb", "serving_size": "100g"}],
                per_food_results=[
                    {
                        "safety_label": food_eval["safety_label"],
                        "explanation": food_eval["explanation"],
                    }
                ],  # type: ignore[arg-type]
                precomputed_totals={"total_gl": 9.8, "total_fiber_g": 0.0, "total_protein_g": 0.0},
            )
            self.assertEqual(meal_result["meal_risk_category"], "medium")


if __name__ == "__main__":
    unittest.main()
