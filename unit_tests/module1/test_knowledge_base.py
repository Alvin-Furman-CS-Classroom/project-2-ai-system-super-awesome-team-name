"""
Unit tests for NutritionKnowledgeBase (Module 1).

Focus: Integration tests, error cases, and edge cases.
Tests assume the CSV is trustworthy and part of the program.
Private methods are tested indirectly through public API.
"""

import unittest
import os
import sys

# Add src to path so we can import knowledge_base
# Use abspath so IDE can resolve the import
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from module1.knowledge_base import (
    NutritionKnowledgeBase,
    FoodNotFoundError,
    MissingDataError,
)


class TestIntegration(unittest.TestCase):
    """Integration tests - test the full workflow through public API."""

    def setUp(self):
        """Set up test knowledge base with actual CSV."""
        csv_path = os.path.join(
            os.path.dirname(__file__), '../../src/module1/nutrition_data.csv'
        )
        self.kb = NutritionKnowledgeBase(csv_path)

    def test_get_nutrition_features_basic(self):
        """Test basic feature lookup with default serving size."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled")
        
        # Check all required keys are present
        required_keys = {
            "glycemic_index", "glycemic_load", "carbohydrates", "fiber",
            "protein", "fat", "processing_level", "serving_size_grams"
        }
        self.assertEqual(set(features.keys()), required_keys)
        
        # Check data types
        self.assertIsInstance(features["glycemic_index"], float)
        self.assertIsInstance(features["glycemic_load"], float)
        self.assertIsInstance(features["carbohydrates"], float)
        self.assertIsInstance(features["fiber"], float)
        self.assertIsInstance(features["protein"], float)
        self.assertIsInstance(features["fat"], float)
        self.assertIsInstance(features["processing_level"], str)
        self.assertIsInstance(features["serving_size_grams"], float)

    def test_get_nutrition_features_default_serving_size(self):
        """Test that default serving size is 100g."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled")
        self.assertEqual(features["serving_size_grams"], 100.0)

    def test_get_nutrition_features_custom_serving_size_grams(self):
        """Test custom serving size in grams."""
        features_100g = self.kb.get_nutrition_features("cabbage cruciferous boiled", "100g")
        features_200g = self.kb.get_nutrition_features("cabbage cruciferous boiled", "200g")
        
        # 200g should have exactly 2x the nutrients
        self.assertEqual(features_200g["carbohydrates"], features_100g["carbohydrates"] * 2)
        self.assertEqual(features_200g["fiber"], features_100g["fiber"] * 2)
        self.assertEqual(features_200g["protein"], features_100g["protein"] * 2)
        self.assertEqual(features_200g["fat"], features_100g["fat"] * 2)
        self.assertEqual(features_200g["serving_size_grams"], 200.0)

    def test_get_nutrition_features_custom_serving_size_servings(self):
        """Test custom serving size in servings."""
        # cabbage has serving_size_grams = 98
        features_1serving = self.kb.get_nutrition_features("cabbage cruciferous boiled", "1 serving")
        features_2servings = self.kb.get_nutrition_features("cabbage cruciferous boiled", "2 servings")
        
        # 2 servings should be 2x the nutrients
        self.assertEqual(features_2servings["carbohydrates"], features_1serving["carbohydrates"] * 2)
        self.assertEqual(features_2servings["serving_size_grams"], 98.0 * 2)

    def test_get_nutrition_features_glycemic_load_calculation(self):
        """Test that glycemic load is calculated correctly: (GI × carbs) / 100."""
        # cabbage: GI=20, carbs per 100g = 6.0
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled", "100g")
        expected_gl = (20.0 * 6.0) / 100
        self.assertAlmostEqual(features["glycemic_load"], expected_gl, places=5)

    def test_get_nutrition_features_scaling_consistency(self):
        """Test that scaling works consistently across different serving sizes."""
        food = "arborio rice boiled"
        
        features_50g = self.kb.get_nutrition_features(food, "50g")
        features_100g = self.kb.get_nutrition_features(food, "100g")
        features_150g = self.kb.get_nutrition_features(food, "150g")
        
        # 50g should be half of 100g
        self.assertAlmostEqual(features_50g["carbohydrates"], features_100g["carbohydrates"] / 2, places=5)
        # 150g should be 1.5x of 100g
        self.assertAlmostEqual(features_150g["carbohydrates"], features_100g["carbohydrates"] * 1.5, places=5)

    def test_get_nutrition_features_name_case_insensitive(self):
        """Test that food lookup is case-insensitive."""
        features1 = self.kb.get_nutrition_features("CABBAGE CRUCIFEROUS BOILED")
        features2 = self.kb.get_nutrition_features("cabbage cruciferous boiled")
        features3 = self.kb.get_nutrition_features("Cabbage Cruciferous Boiled")
        
        self.assertEqual(features1["glycemic_index"], features2["glycemic_index"])
        self.assertEqual(features2["glycemic_index"], features3["glycemic_index"])

    def test_get_nutrition_features_name_whitespace(self):
        """Test that food lookup handles whitespace variations."""
        features1 = self.kb.get_nutrition_features("  cabbage cruciferous   boiled  ")
        features2 = self.kb.get_nutrition_features("cabbage cruciferous boiled")
        
        self.assertEqual(features1["glycemic_index"], features2["glycemic_index"])

    def test_list_all_foods(self):
        """Test that list_all_foods returns all food names."""
        foods = self.kb.list_all_foods()
        
        self.assertIsInstance(foods, list)
        self.assertGreater(len(foods), 0)
        self.assertIn("cabbage cruciferous boiled", foods)
        # All entries should be strings
        for food in foods:
            self.assertIsInstance(food, str)

    def test_get_all_foods(self):
        """Test that get_all_foods returns a copy of all data."""
        all_foods = self.kb.get_all_foods()
        
        self.assertIsInstance(all_foods, dict)
        self.assertGreater(len(all_foods), 0)
        # Should contain the same keys as list_all_foods
        self.assertEqual(set(all_foods.keys()), set(self.kb.list_all_foods()))
        
        # Should be a copy (modifying it doesn't affect internal data)
        original_count = len(all_foods)
        all_foods["test_key"] = "test_value"
        self.assertEqual(len(self.kb.get_all_foods()), original_count)
        self.assertNotIn("test_key", self.kb.get_all_foods())

    def test_multiple_foods_sequence(self):
        """Test looking up multiple different foods in sequence."""
        foods_to_test = [
            "cabbage cruciferous boiled",
            "deli turkey poached",
            "arborio rice boiled",
        ]
        
        for food in foods_to_test:
            features = self.kb.get_nutrition_features(food)
            self.assertIsNotNone(features["glycemic_index"])
            self.assertIsNotNone(features["carbohydrates"])


class TestErrors(unittest.TestCase):
    """Test all error cases - user-facing errors only."""

    def setUp(self):
        """Set up test knowledge base."""
        csv_path = os.path.join(
            os.path.dirname(__file__), '../../src/module1/nutrition_data.csv'
        )
        self.kb = NutritionKnowledgeBase(csv_path)

    def test_food_not_found_error(self):
        """Test FoodNotFoundError for unknown food."""
        with self.assertRaises(FoodNotFoundError) as context:
            self.kb.get_nutrition_features("nonexistent food xyz")
        
        error = context.exception
        self.assertEqual(error.food_name, "nonexistent food xyz")
        self.assertIn("not found", str(error).lower())

    def test_food_not_found_error_message(self):
        """Test that FoodNotFoundError message includes food name."""
        with self.assertRaises(FoodNotFoundError) as context:
            self.kb.get_nutrition_features("pizza margherita")
        
        error_msg = str(context.exception)
        self.assertIn("pizza margherita", error_msg)

    def test_invalid_serving_size_empty_string(self):
        """Test ValueError for empty serving size string."""
        with self.assertRaises(ValueError):
            self.kb.get_nutrition_features("cabbage cruciferous boiled", "")

    def test_invalid_serving_size_invalid_format(self):
        """Test ValueError for unrecognized serving size format."""
        with self.assertRaises(ValueError):
            self.kb.get_nutrition_features("cabbage cruciferous boiled", "invalid format")

    def test_invalid_serving_size_negative_grams(self):
        """Test ValueError for negative grams."""
        with self.assertRaises(ValueError):
            self.kb.get_nutrition_features("cabbage cruciferous boiled", "-100g")

    def test_invalid_serving_size_negative_servings(self):
        """Test ValueError for negative servings."""
        with self.assertRaises(ValueError):
            self.kb.get_nutrition_features("cabbage cruciferous boiled", "-1 serving")

    def test_invalid_serving_size_no_number(self):
        """Test ValueError for serving size with no number."""
        with self.assertRaises(ValueError):
            self.kb.get_nutrition_features("cabbage cruciferous boiled", "g")
        
        with self.assertRaises(ValueError):
            self.kb.get_nutrition_features("cabbage cruciferous boiled", "serving")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test knowledge base."""
        csv_path = os.path.join(
            os.path.dirname(__file__), '../../src/module1/nutrition_data.csv'
        )
        self.kb = NutritionKnowledgeBase(csv_path)

    def test_zero_gi_food(self):
        """Test food with GI=0 (like meat/protein foods)."""
        features = self.kb.get_nutrition_features("deli turkey poached")
        self.assertEqual(features["glycemic_index"], 0.0)
        # GL should be 0 when GI is 0
        self.assertEqual(features["glycemic_load"], 0.0)

    def test_zero_carbs_food(self):
        """Test food with very low carbs."""
        features = self.kb.get_nutrition_features("deli turkey poached", "100g")
        # deli turkey has 0.3 carbs per 100g, so GL should be (0 * 0.3) / 100 = 0
        self.assertEqual(features["glycemic_load"], 0.0)

    def test_zero_serving_size(self):
        """Test serving size of 0g."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled", "0g")
        self.assertEqual(features["serving_size_grams"], 0.0)
        self.assertEqual(features["carbohydrates"], 0.0)
        self.assertEqual(features["fiber"], 0.0)
        self.assertEqual(features["protein"], 0.0)
        self.assertEqual(features["fat"], 0.0)
        self.assertEqual(features["glycemic_load"], 0.0)

    def test_zero_servings(self):
        """Test serving size of 0 servings."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled", "0 serving")
        self.assertEqual(features["serving_size_grams"], 0.0)
        self.assertEqual(features["carbohydrates"], 0.0)

    def test_very_large_serving_size(self):
        """Test very large serving size."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled", "1000g")
        self.assertEqual(features["serving_size_grams"], 1000.0)
        # Should scale correctly (10x for 1000g vs 100g)
        features_100g = self.kb.get_nutrition_features("cabbage cruciferous boiled", "100g")
        self.assertAlmostEqual(features["carbohydrates"], features_100g["carbohydrates"] * 10, places=5)

    def test_fractional_servings(self):
        """Test fractional serving sizes."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled", "0.5 serving")
        # cabbage base serving is 98g, so 0.5 serving = 49g
        self.assertEqual(features["serving_size_grams"], 49.0)
        
        features_2_5 = self.kb.get_nutrition_features("cabbage cruciferous boiled", "2.5 servings")
        self.assertEqual(features_2_5["serving_size_grams"], 98.0 * 2.5)

    def test_decimal_grams(self):
        """Test serving size with decimal grams."""
        features = self.kb.get_nutrition_features("cabbage cruciferous boiled", "50.5g")
        self.assertEqual(features["serving_size_grams"], 50.5)

    def test_space_before_g(self):
        """Test serving size with space before 'g'."""
        features1 = self.kb.get_nutrition_features("cabbage cruciferous boiled", "100g")
        features2 = self.kb.get_nutrition_features("cabbage cruciferous boiled", "100 g")
        self.assertEqual(features1["serving_size_grams"], features2["serving_size_grams"])

    def test_high_gi_food(self):
        """Test food with high GI (like white rice)."""
        features = self.kb.get_nutrition_features("arborio rice boiled", "100g")
        # arborio rice has GI=94, should have high GL
        self.assertGreater(features["glycemic_index"], 70.0)
        self.assertGreater(features["glycemic_load"], 0.0)

    def test_different_processing_levels(self):
        """Test that processing_level is preserved correctly."""
        whole_food = self.kb.get_nutrition_features("cabbage cruciferous boiled")
        processed_food = self.kb.get_nutrition_features("arborio rice boiled")
        
        self.assertEqual(whole_food["processing_level"], "whole")
        self.assertEqual(processed_food["processing_level"], "processed")

    def test_name_with_multiple_spaces(self):
        """Test food name with multiple spaces."""
        features = self.kb.get_nutrition_features("cabbage   cruciferous   boiled")
        # Should still find the food (normalization handles multiple spaces)
        self.assertIsNotNone(features["glycemic_index"])


if __name__ == '__main__':
    unittest.main()
