"""
Nutrition Knowledge Base: loads nutrition data from CSV and provides feature lookup.

Knowledge representation: CSV file.
In-memory knowledge base: dict mapping food name -> nutrition data.

Created 1/30/2026
Authors: Jia Lin and Della Avent
Last Updated: 2/3/2026
"""

import csv
from typing import Dict, List

# Numeric columns in CSV that should be converted to float during loading
_FLOAT_KEYS = ("glycemic_index", "carbohydrates", "fiber", "protein", "fat", "serving_size_grams")

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
    """Initialize the knowledge base and load nutrition data from CSV.
    
    Args:
        csv_path: Path to CSV file. Defaults to "nutrition_data.csv".
    
    Raises:
        FileNotFoundError: If CSV file cannot be found.
        ValueError: If CSV is malformed or missing required columns.
    """
    def __init__(self, csv_path: str = "nutrition_data.csv") -> None:
        self.data = self._load_csv(csv_path)

    """Return structured nutrition features for a food at the given serving size.
    
    Args:
        food_name: Food name (case-insensitive, whitespace-tolerant).
        serving_size: Serving size string. Formats: "100g", "200 g", "1 serving", "2.5 servings".
                     Defaults to "100g".
    
    Returns:
        Dict with keys: glycemic_index, glycemic_load, carbohydrates, fiber, protein, fat,
        processing_level, serving_size_grams. All nutrients are per serving.
    
    Raises:
        FoodNotFoundError: If food name not found.
        MissingDataError: If required nutrition data missing.
        ValueError: If serving_size format invalid or negative.
    """
    def get_nutrition_features(self, food_name: str, serving_size: str = "100g") -> dict:
        # Normalize the food name.
        normalized_name = self._normalize_name(food_name)
        # Look up normalized name in self.data; if missing, raise FoodNotFoundError.
        if normalized_name not in self.data:
            raise FoodNotFoundError(f"Food {food_name} not found in the knowledge base.", food_name)
        # Get this food's nutrition row from the dict.
        food_data = self.data[normalized_name]
        # Require all fields needed for features; raise MissingDataError if any are missing.
        required_keys = (
            "glycemic_index", "carbohydrates", "fiber", "protein", "fat",
            "serving_size_grams", "processing_level",
        )
        # there shouldn't be any missing keys, but just in case, check for them
        missing = [k for k in required_keys if food_data.get(k) is None]
        if missing:
            raise MissingDataError(
                f"Missing data for {food_name}: {', '.join(missing)}", food_name
            )
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
        # Build and return one dict with GI, GL, macronutrients, processing_level, serving info.
        return {"glycemic_index": food_data["glycemic_index"], 
                "glycemic_load": glycemic_load, 
                "carbohydrates": scaled_carbs, 
                "fiber": scaled_fiber, 
                "protein": scaled_protein, 
                "fat": scaled_fat, 
                "processing_level": food_data["processing_level"], 
                "serving_size_grams": serving_grams}

    """Return list of all food names in the knowledge base.
    
    Returns:
        List of normalized food name strings (lowercase, whitespace-normalized).
    """
    def list_all_foods(self) -> List[str]:
        return list(self.data.keys())

    """Return copy of all food data in the knowledge base.
    
    Returns:
        Dict mapping normalized food names to nutrition data dicts.
        Each dict contains: glycemic_index, carbohydrates, fiber, protein, fat,
        processing_level, serving_size_grams (all per 100g). Returns a copy.
    """
    def get_all_foods(self) -> Dict:
        return self.data.copy()

    """Load CSV file into dictionary. Keys are normalized food names.
    
    Numeric columns (from _FLOAT_KEYS) are converted to float; empty cells become None.
    
    Args:
        filepath: Path to CSV file.
    
    Returns:
        Dict mapping normalized food names to nutrition data dicts.
    
    Raises:
        FileNotFoundError: If file cannot be found.
        ValueError: If CSV is malformed or missing required columns.
    """
    def _load_csv(self, filepath: str) -> Dict:
        nutrition_dict: Dict = {}

        with open(filepath, "r", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                normalized_name = self._normalize_name((row.get("name") or "").strip())
                # create a dictionary for the row
                entry = {k: (v or "").strip() or None for k, v in row.items()}
                # go through the dictionary and convert the strings to floats where necessary
                for k in _FLOAT_KEYS:
                    v = entry.get(k)
                    entry[k] = float(v) if v else None
                nutrition_dict[normalized_name] = entry
        return nutrition_dict

    """Normalize food name (lowercase, strip whitespace, collapse spaces).
    
    Note: Does not currently handle synonyms/plurals (e.g., "apple" vs "apples").
    
    Args:
        name: Food name string to normalize.
    
    Returns:
        Normalized name string (lowercase, whitespace-collapsed).
    """
    def _normalize_name(self, name: str) -> str:
        if not name:
            return ""
        # lowercase, strip, collapse repeated spaces
        return " ".join(name.lower().strip().split())

    """Compute glycemic load: (GI × carbs per serving) / 100.
    
    Args:
        gi: Glycemic index value.
        carbs_per_serving: Carbohydrates in grams for the serving.
    
    Returns:
        Glycemic load value (float).
    """
    def _calculate_glycemic_load(self, gi: float, carbs_per_serving: float) -> float:
        return (gi * carbs_per_serving) / 100

    """Parse serving size string and return total grams.
    
    Supports formats: "100g", "200 g", "1 serving", "2.5 servings".
    
    Args:
        serving_str: Serving size string to parse.
        base_grams: Base serving size in grams (for "serving" format).
    
    Returns:
        Total grams for the requested serving size.
    
    Raises:
        ValueError: If serving size format is unrecognized, empty, or negative.
    """
    def _convert_serving_size(self, serving_str: str, base_grams: float) -> float:
        s = serving_str.strip().lower()
        if not s:
            raise ValueError("Serving size string is empty")

        # "1 serving", "2.5 servings" -> number * base_grams
        # Check this BEFORE checking for "g" to avoid misparsing "serving" as ending with "g"
        if "serving" in s:
            parts = s.split()
            if not parts:
                raise ValueError(f"Invalid serving format: {serving_str!r}")
            try:
                count = float(parts[0])
            except ValueError:
                raise ValueError(f"Invalid serving format: {serving_str!r}")
            if count < 0:
                raise ValueError("Serving count cannot be negative")
            return count * base_grams

        # "100g" or "200 g" -> grams
        if s.endswith("g"):
            num_str = s[:-1].strip()
            try:
                grams = float(num_str)
            except ValueError:
                raise ValueError(f"Invalid grams format: {serving_str!r}")
            if grams < 0:
                raise ValueError("Grams cannot be negative")
            return grams

        raise ValueError(f"Unrecognized serving size format: {serving_str!r}")
