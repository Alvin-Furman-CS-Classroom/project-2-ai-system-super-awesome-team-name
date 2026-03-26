"""
Unit tests for FoodSafetyEngine (Module 2).

Tests init validation, evaluate_food return shape and labels, and propagation
of Module 1 errors. Uses real NutritionKnowledgeBase (and a small subclass for
error injection) so the engine's isinstance check is satisfied.
"""

import unittest
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module1.knowledge_base import NutritionKnowledgeBase, FoodNotFoundError, MissingDataError
from src.module2.food_safety_engine import FoodSafetyEngine

_CSV_PATH = os.path.join(os.path.dirname(__file__), '../../src/module1/nutrition_data.csv')


class _MockKB(NutritionKnowledgeBase):
    """Subclass that overrides get_nutrition_features to inject return value or error."""

    def __init__(self, features=None, raise_error=None):
        super().__init__(_CSV_PATH)
        self._mock_features = features
        self._mock_error = raise_error
        self.last_food_name = None
        self.last_serving_size = None

    def get_nutrition_features(self, food_name: str, serving_size: str = "100g"):
        self.last_food_name = food_name
        self.last_serving_size = serving_size
        if self._mock_error is not None:
            raise self._mock_error
        return self._mock_features


class TestFoodSafetyEngineInit(unittest.TestCase):
    """Tests for FoodSafetyEngine constructor."""

    def test_init_accepts_nutrition_knowledge_base(self):
        """Engine accepts a real NutritionKnowledgeBase (requires data file)."""
        kb = NutritionKnowledgeBase(_CSV_PATH)
        engine = FoodSafetyEngine(kb)
        self.assertIs(engine.knowledge_base, kb)

    def test_init_rejects_non_kb_type(self):
        """Engine raises TypeError if knowledge_base is not NutritionKnowledgeBase."""
        with self.assertRaises(TypeError) as context:
            FoodSafetyEngine(None)
        self.assertIn("NutritionKnowledgeBase", str(context.exception))

        with self.assertRaises(TypeError):
            FoodSafetyEngine("not a kb")

    def test_init_accepts_optional_thresholds(self):
        """Engine accepts optional thresholds dict without error."""
        kb = NutritionKnowledgeBase(_CSV_PATH)
        engine = FoodSafetyEngine(kb, thresholds={"safe_gl": 10.0})
        self.assertEqual(engine._thresholds, {"safe_gl": 10.0})


class TestFoodSafetyEngineEvaluate(unittest.TestCase):
    """Tests for evaluate_food (using mock KB subclass for isolation)."""

    def test_evaluate_returns_safety_label_and_explanation(self):
        """evaluate_food returns dict with safety_label and explanation."""
        features = {
            "glycemic_index": 50.0,
            "glycemic_load": 8.0,
            "carbohydrates": 20.0,
            "fiber": 2.0,
            "protein": 1.0,
            "fat": 0.0,
            "processing_level": "whole",
            "serving_size_grams": 100.0,
        }
        mock_kb = _MockKB(features=features)
        engine = FoodSafetyEngine(mock_kb)
        result = engine.evaluate_food("test food", "100g")
        self.assertIsInstance(result, dict)
        self.assertIn("safety_label", result)
        self.assertIn("explanation", result)
        self.assertIn(result["safety_label"], ("safe", "caution", "unsafe"))
        self.assertIsInstance(result["explanation"], str)

    def test_evaluate_passes_food_name_and_serving_to_kb(self):
        """evaluate_food forwards food_name and serving_size to knowledge base."""
        features = {
            "glycemic_index": 50.0,
            "glycemic_load": 8.0,
            "carbohydrates": 20.0,
            "fiber": 2.0,
            "protein": 1.0,
            "fat": 0.0,
            "processing_level": "whole",
            "serving_size_grams": 200.0,
        }
        mock_kb = _MockKB(features=features)
        engine = FoodSafetyEngine(mock_kb)
        engine.evaluate_food("my food", "200g")
        self.assertEqual(mock_kb.last_food_name, "my food")
        self.assertEqual(mock_kb.last_serving_size, "200g")

    def test_evaluate_default_serving_size(self):
        """evaluate_food uses default serving size when not provided."""
        features = {
            "glycemic_index": 50.0,
            "glycemic_load": 8.0,
            "carbohydrates": 20.0,
            "fiber": 2.0,
            "protein": 1.0,
            "fat": 0.0,
            "processing_level": "whole",
            "serving_size_grams": 100.0,
        }
        mock_kb = _MockKB(features=features)
        engine = FoodSafetyEngine(mock_kb)
        engine.evaluate_food("food")
        self.assertEqual(mock_kb.last_serving_size, "100g")

    def test_evaluate_safe_label_for_low_gi_gl(self):
        """Low GI and GL produce safe label."""
        features = {
            "glycemic_index": 40.0,
            "glycemic_load": 5.0,
            "carbohydrates": 15.0,
            "fiber": 3.0,
            "protein": 2.0,
            "fat": 0.5,
            "processing_level": "whole",
            "serving_size_grams": 100.0,
        }
        mock_kb = _MockKB(features=features)
        engine = FoodSafetyEngine(mock_kb)
        result = engine.evaluate_food("low gi food")
        self.assertEqual(result["safety_label"], "safe")

    def test_evaluate_unsafe_label_for_high_gi(self):
        """High GI produces unsafe label."""
        features = {
            "glycemic_index": 85.0,
            "glycemic_load": 10.0,
            "carbohydrates": 25.0,
            "fiber": 1.0,
            "protein": 2.0,
            "fat": 0.0,
            "processing_level": "processed",
            "serving_size_grams": 100.0,
        }
        mock_kb = _MockKB(features=features)
        engine = FoodSafetyEngine(mock_kb)
        result = engine.evaluate_food("high gi food")
        self.assertEqual(result["safety_label"], "unsafe")

    def test_evaluate_unsafe_label_for_high_gl(self):
        """High GL produces unsafe label even if GI is safe."""
        features = {
            "glycemic_index": 50.0,   # safe GI
            "glycemic_load": 25.0,    # unsafe GL
            "carbohydrates": 60.0,
            "fiber": 5.0,
            "protein": 5.0,
            "fat": 1.0,
            "processing_level": "processed",
            "serving_size_grams": 200.0,
        }
        mock_kb = _MockKB(features=features)
        engine = FoodSafetyEngine(mock_kb)
        result = engine.evaluate_food("high gl food")
        self.assertEqual(result["safety_label"], "unsafe")


class TestFoodSafetyEngineErrorPropagation(unittest.TestCase):
    """Tests that Module 1 errors are propagated by evaluate_food."""

    def test_propagates_food_not_found_error(self):
        """FoodNotFoundError from KB is propagated."""
        mock_kb = _MockKB(raise_error=FoodNotFoundError("Not found", "unknown"))
        engine = FoodSafetyEngine(mock_kb)
        with self.assertRaises(FoodNotFoundError) as context:
            engine.evaluate_food("unknown")
        self.assertEqual(context.exception.food_name, "unknown")

    def test_propagates_missing_data_error(self):
        """MissingDataError from KB is propagated."""
        mock_kb = _MockKB(
            raise_error=MissingDataError("Missing glycemic_index", "some food")
        )
        engine = FoodSafetyEngine(mock_kb)
        with self.assertRaises(MissingDataError):
            engine.evaluate_food("some food")

    def test_propagates_value_error(self):
        """ValueError from KB (e.g. invalid serving size) is propagated."""
        mock_kb = _MockKB(raise_error=ValueError("Invalid serving size"))
        engine = FoodSafetyEngine(mock_kb)
        with self.assertRaises(ValueError):
            engine.evaluate_food("food", "invalid")


if __name__ == "__main__":
    unittest.main()
