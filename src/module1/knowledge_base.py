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

    pass

# Raised when a requested food has missing data.
class MissingDataError(Exception):

    pass


class NutritionKnowledgeBase:
    """
    In-memory knowledge base of nutrition data loaded from CSV.
    Supports lookup by food name and feature extraction (GI, GL, macronutrients).
    """
    # Initialize the knowledge base and load nutrition_data.csv
    def __init__(self) -> None:
        pass

    # Return structured nutrition features for a food at the given serving size.
    def get_nutrition_features(self, food_name: str, serving_size: str = "100g") -> dict:
      
        pass

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
