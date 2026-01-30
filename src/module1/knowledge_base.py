"""
Nutrition Knowledge Base: loads nutrition data from CSV and provides feature lookup.

Knowledge representation: CSV file.
In-memory knowledge base: dict mapping food name -> nutrition data.
"""

# so that the code is easier to read and understand
from typing import Dict, List


class FoodNotFoundError(Exception):
    """Raised when a requested food is not in the knowledge base."""

    pass


class NutritionKnowledgeBase:
    """
    In-memory knowledge base of nutrition data loaded from CSV.
    Supports lookup by food name and feature extraction (GI, GL, macronutrients).
    """

    def __init__(self, csv_file: str = None) -> None:
        """
        Initialize the knowledge base and load nutrition data from CSV.
        If csv_file is None, load from default nutrition_data.csv.
        """
        pass

    def get_nutrition_features(self, food_name: str, serving_size: str = "100g") -> dict:
        """
        Return structured nutrition features for a food at the given serving size.
        Main client-facing method.
        """
        pass

    def list_all_foods(self) -> List[str]:
        """Return list of all food names in the knowledge base (for Module 4 search)."""
        pass

    def get_all_foods(self) -> Dict:
        """Return copy of all food data (for Module 4 to search for swaps)."""
        pass

    def _load_csv(self, filepath: str) -> Dict:
        """Load CSV file into dict. Keys are normalized food names."""
        pass

    def _normalize_name(self, name: str) -> str:
        """Normalize food name (e.g. lowercase, strip whitespace)."""
        pass

    def _calculate_glycemic_load(self, gi: float, carbs_per_serving: float) -> float:
        """Compute glycemic load: (GI × carbs per serving) / 100."""
        pass

    def _convert_serving_size(self, serving_str: str, base_grams: float) -> float:
        """Parse serving size string and convert to grams."""
        pass
