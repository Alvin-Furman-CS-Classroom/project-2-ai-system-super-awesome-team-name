"""Module 4: Meal modification search and suggestions."""

from .meal_suggestion_planner import (
    MealSuggestionPlanner,
    infer_food_category,
    infer_grain_starch_subfamily,
    meal_has_duplicate_replacement_across_distinct_foods,
    suggestion_count_for_category,
)

__all__ = [
    "MealSuggestionPlanner",
    "infer_food_category",
    "infer_grain_starch_subfamily",
    "meal_has_duplicate_replacement_across_distinct_foods",
    "suggestion_count_for_category",
]
