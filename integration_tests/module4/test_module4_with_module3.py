import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module1.knowledge_base import NutritionKnowledgeBase
from src.module2.food_safety_engine import FoodSafetyEngine
from src.module3.meal_risk_analyzer import MealRiskAnalyzer
from src.module4.meal_suggestion_planner import MealSuggestionPlanner


class TestModule4Integration(unittest.TestCase):
    def test_module4_generates_tier_drop_suggestions(self):
        kb = NutritionKnowledgeBase("src/module1/nutrition_data.csv")
        safety_engine = FoodSafetyEngine(kb)
        analyzer = MealRiskAnalyzer(
            knowledge_base=kb,
            food_safety_engine=safety_engine,
            enable_effective_gl_adjustments=True,
        )
        planner = MealSuggestionPlanner(kb, analyzer, matcher=None, max_edits=3, max_expansions=140)

        meal_items = [
            {"food_name": "arborio rice boiled", "serving_size": "100g"},
            {"food_name": "bagel bread stale", "serving_size": "100g"},
        ]
        original = analyzer.analyze_meal(meal_items)
        result = planner.generate_suggestions(
            meal_items,
            original_category=original["meal_risk_category"],
            algorithm="astar",
        )

        if original["meal_risk_category"] in ("medium", "high"):
            self.assertGreaterEqual(len(result["suggestions"]), 1)
            for suggestion in result["suggestions"]:
                self.assertLessEqual(len(suggestion["actions"]), 5)


if __name__ == "__main__":
    unittest.main()
