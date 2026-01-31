"""
Nutrition Knowledge Base: loads nutrition data from CSV and provides feature lookup.

Knowledge representation: CSV file.
In-memory knowledge base: dict mapping food name -> nutrition data.

Created 1/30/2026
Authors: Jia Lin and Della Avent
Last Updated: 1/30/2026
"""

# so that the code is easier to read and understand
from typing import Dict, List

# Raised when a requested food is not in the knowledge base.
class FoodNotFoundError(Exception):
    def __init__(self, message: str, food_name: str):
        super().__init__(message)
        self.food_name = food_name


# Raised when a requested food has missing data.
class MissingDataError(Exception):
    def __init__(self, message: str, food_name: str):
        super().__init__(message)
        self.food_name = food_name


class NutritionKnowledgeBase:
    """
    In-memory knowledge base of nutrition data loaded from CSV.
    Supports lookup by food name and feature extraction (GI, GL, macronutrients).
    """
    # Initialize the knowledge base and load nutrition_data.csv
    def __init__(self) -> None:
        self.data = self._load_csv("nutrition_data.csv")

    # Return structured nutrition features for a food at the given serving size.
    def get_nutrition_features(self, food_name: str, serving_size: str = "100g") -> dict:
        # Normalize the food name.
        normalized_name = self._normalize_name(food_name)
        # Look up normalized name in self.data; if missing, raise FoodNotFoundError.
        if normalized_name not in self.data:
            raise FoodNotFoundError(f"Food {food_name} not found in the knowledge base.", food_name)
        # Get this food's nutrition row from the dict.
        food_data = self.data[normalized_name]
        # Convert serving_size to grams using _convert_serving_size.
        serving_grams = self._convert_serving_size(serving_size, food_data["serving_size_grams"])
        # Scale nutrients (carbs, fiber, protein, fat) to that serving: per_100g * (serving_grams / 100).
        scale = serving_grams / 100
        scaled_carbs = food_data["carbohydrates"] * scale
        scaled_fiber = food_data["fiber"] * scale
        scaled_protein = food_data["protein"] * scale
        scaled_fat = food_data["fat"] * scale
        # Compute glycemic load for this serving with _calculate_glycemic_load.
        glycemic_load = self._calculate_glycemic_load(food_data["glycemic_index"], scaled_carbs)
        # If required fields are missing/invalid, raise MissingDataError.
        if food_data["glycemic_index"] is None or scaled_carbs is None:
            raise MissingDataError(f"Missing data for {food_name}", food_name)
        # Build and return one dict with GI, GL, macronutrients, processing_level, serving info.
        return {glycemic_index: food_data["glycemic_index"], 
                glycemic_load: glycemic_load, 
                carbohydrates: scaled_carbs, 
                fiber: scaled_fiber, 
                protein: scaled_protein, 
                fat: scaled_fat, 
                processing_level: food_data["processing_level"], 
                serving_size_grams: serving_grams}

    # Return list of all food names in the knowledge base (for Module 4 search).
    def list_all_foods(self) -> List[str]:
        pass

    # Return copy of all food data (for Module 4 to search for swaps).
    def get_all_foods(self) -> Dict:
        pass

    # Load CSV file into dict. Keys are normalized food names.
    def _load_csv(self, filepath: str) -> Dict:
        pass

    # Normalize food name (e.g. lowercase, strip whitespace).
    def _normalize_name(self, name: str) -> str:
        pass

    # Compute glycemic load: (GI × carbs per serving) / 100.
    def _calculate_glycemic_load(self, gi: float, carbs_per_serving: float) -> float:
        pass

    # Parse serving size string and convert to grams.
    def _convert_serving_size(self, serving_str: str, base_grams: float) -> float:
        pass
