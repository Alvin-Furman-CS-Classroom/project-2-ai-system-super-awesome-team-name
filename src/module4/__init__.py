"""Module 4: Meal modification search and suggestions."""

from .meal_suggestion_planner import (
    MealSuggestionPlanner,
    infer_food_category,
    suggestion_count_for_category,
)

__all__ = [
    "MealSuggestionPlanner",
    "infer_food_category",
    "suggestion_count_for_category",
]
