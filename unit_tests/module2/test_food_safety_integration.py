"""
Integration tests for Module 2 with Module 1.

Uses real NutritionKnowledgeBase (CSV data) and FoodSafetyEngine together:
end-to-end food name + serving size -> safety label + explanation.
"""

import unittest
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module1.knowledge_base import NutritionKnowledgeBase, FoodNotFoundError
from src.module2.food_safety_engine import FoodSafetyEngine

_CSV_PATH = os.path.join(os.path.dirname(__file__), '../../src/module1/nutrition_data.csv')


class TestFoodSafetyIntegration(unittest.TestCase):
    """End-to-end: KB + Engine for real foods from CSV."""

    def setUp(self):
        self.kb = NutritionKnowledgeBase(_CSV_PATH)
        self.engine = FoodSafetyEngine(self.kb)

    def test_low_gi_food_safe(self):
        """Cabbage (low GI/GL) is classified safe."""
        result = self.engine.evaluate_food("cabbage cruciferous boiled")
        self.assertEqual(result["safety_label"], "safe")
        self.assertIn("safe", result["explanation"].lower() or result["explanation"])

    def test_high_gi_food_unsafe(self):
        """Arborio rice (high GI) is classified unsafe at 100g."""
        result = self.engine.evaluate_food("arborio rice boiled", "100g")
        self.assertEqual(result["safety_label"], "unsafe")

    def test_protein_food_safe(self):
        """Deli turkey (GI 0, low carbs) is safe."""
        result = self.engine.evaluate_food("deli turkey poached")
        self.assertEqual(result["safety_label"], "safe")

    def test_serving_size_affects_label(self):
        """Larger serving can change scaling and thus GL; result has label and explanation."""
        result_small = self.engine.evaluate_food("arborio rice boiled", "50g")
        result_large = self.engine.evaluate_food("arborio rice boiled", "200g")
        self.assertIn(result_small["safety_label"], ("safe", "caution", "unsafe"))
        self.assertIn(result_large["safety_label"], ("safe", "caution", "unsafe"))
        self.assertIsInstance(result_small["explanation"], str)
        self.assertIsInstance(result_large["explanation"], str)

    def test_case_insensitive_lookup(self):
        """Food name is case-insensitive (KB + engine)."""
        r1 = self.engine.evaluate_food("CABBAGE CRUCIFEROUS BOILED")
        r2 = self.engine.evaluate_food("cabbage cruciferous boiled")
        self.assertEqual(r1["safety_label"], r2["safety_label"])

    def test_unknown_food_raises(self):
        """Unknown food raises FoodNotFoundError through engine."""
        with self.assertRaises(FoodNotFoundError) as context:
            self.engine.evaluate_food("nonexistent food xyz")
        self.assertIn("nonexistent", context.exception.food_name.lower()
                      or str(context.exception).lower())

    def test_invalid_serving_raises(self):
        """Invalid serving size raises ValueError through engine."""
        with self.assertRaises(ValueError):
            self.engine.evaluate_food("cabbage cruciferous boiled", "invalid")

    def test_explanation_describes_gl_and_gi(self):
        """Explanation mentions glycemic load and index for transparency."""
        result = self.engine.evaluate_food("cabbage cruciferous boiled")
        self.assertIn("Glycemic load", result["explanation"])
        self.assertIn("Glycemic index", result["explanation"])


if __name__ == "__main__":
    unittest.main()

