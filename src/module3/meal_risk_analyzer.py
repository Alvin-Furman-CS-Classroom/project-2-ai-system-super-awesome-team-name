"""
Meal-Level Risk Analyzer (Module 3).

Goal
----
Aggregate Module 2 outputs (per-food safety labels + explanations) into an
overall meal-level risk category and numeric risk score.

In addition to labels-only aggregation, this module can optionally compute
an "effective glycemic load" (effective GL) where:
  - Meal fiber reduces effective GL
  - Meal protein also reduces effective GL

This lets the meal-level decision avoid "worst-food dominates" behavior.

Design notes
-------------
- Module 1 provides nutrition totals (carbs, fiber, protein, GL, etc.)
- Module 2 provides per-food `safety_label` ("safe"|"caution"|"unsafe")
- Module 3 combines both into meal category/score and a human explanation

This file is a scaffolding / implementation checklist. The functions below
describe what you need to implement; they intentionally contain no full logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, TypedDict, Tuple, Literal, Any

from src.module1.knowledge_base import NutritionKnowledgeBase
from src.module2.food_safety_engine import FoodSafetyEngine

MealRiskCategory = Literal["low", "medium", "high"]
FoodSafetyLabel = Literal["safe", "caution", "unsafe"]


class MealItem(TypedDict):
    """A single meal entry with a food and serving size."""

    food_name: str
    serving_size: str
    


class PerFoodSafetyResult(TypedDict):
    """
    Output shape produced by Module 2 for one food.
    """

    safety_label: FoodSafetyLabel
    explanation: str


class MealAnalysisResult(TypedDict):
    """
    Output shape for Module 3.

    Fields:
      - meal_risk_category: low/medium/high
      - risk_score: numeric 0-100
      - contributing_factors: list of strings for user-facing explanation
    """

    meal_risk_category: MealRiskCategory
    risk_score: float
    contributing_factors: List[str]

    # Optional debug/insight fields (useful for tests + UI):
    # total_gl: float
    # effective_gl: float
    # total_fiber_g: float
    # total_protein_g: float


@dataclass(frozen=True)
class EffectiveGLReduction:
    """Details of how fiber/protein reductions changed GL."""

    fiber_multiplier: float
    protein_multiplier: float
    effective_gl: float
    fiber_reduction_pct: float
    protein_reduction_pct: float


class MealRiskAnalyzer:
    """
    Public entry point for Module 3.

    You can implement Module 3 in two modes:
      1) labels-only: use per-food `safety_label` to aggregate meal risk
      2) labels + nutrition totals: compute total GL and adjust to effective GL
    """

    def __init__(
        self,
        knowledge_base: NutritionKnowledgeBase,
        food_safety_engine: FoodSafetyEngine,
        *,
        enable_effective_gl_adjustments: bool = True,
    ) -> None:
        """
        Args:
          knowledge_base: Module 1 KB for nutrition totals.
          food_safety_engine: Module 2 engine for per-food safety labels.
          enable_effective_gl_adjustments:
            If False, meal risk should use labels-only aggregation.
        """
        self.knowledge_base = knowledge_base
        self.food_safety_engine = food_safety_engine
        self.enable_effective_gl_adjustments = enable_effective_gl_adjustments

    # ---------------------------------------------------------------------
    # 1) Orchestration method (recommended)
    # ---------------------------------------------------------------------
    def analyze_meal(
        self,
        meal_items: Sequence[MealItem],
    ) -> MealAnalysisResult:
        """
        Main orchestrator for Module 3.

        Inputs:
          meal_items: list of {"food_name": str, "serving_size": str}

        Steps you should implement:
          1. Validate meal_items is non-empty and has required keys
          2. For each item:
             - call Module 2 to get per-food safety label + explanation
             - call Module 1 to get nutrition features for totals (GI/GL/fiber/protein)
          3. Combine per-food safety labels:
             - compute label-based meal category and factors
          4. If enable_effective_gl_adjustments:
             - sum total GL, total fiber (g), total protein (g)
             - compute effective_gl = total_gl * fiber_multiplier * protein_multiplier
             - compute meal category using thresholds for effective_gl
             - include both label factors and numeric total factors

        Output:
          A MealAnalysisResult dict with category/score/factors.
        """
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # 2) Labels-only aggregation helpers
    # ---------------------------------------------------------------------
    def aggregate_from_labels(
        self,
        per_food_results: Sequence[PerFoodSafetyResult],
    ) -> Tuple[MealRiskCategory, float, List[str]]:
        """
        Aggregate meal risk only from per-food labels.

        Suggested logic:
          - if any label == "unsafe":
              category = "high"
          - elif any label == "caution":
              category = "medium"
          - else category = "low"

        Suggested scoring:
          - risk_score can depend on counts, e.g.
              risk_score = 100 * (unsafe_count*1.0 + caution_count*0.5) / meal_size

        Suggested contributing_factors:
          - "Contains unsafe food(s)" / "Contains caution food(s)" / "All foods safe"
          - optionally list how many safe/caution/unsafe items
        """
        raise NotImplementedError

    def _exists_label(
        self,
        per_food_results: Sequence[PerFoodSafetyResult],
        label: FoodSafetyLabel,
    ) -> bool:
        """
        Helper for FOL-like "exists food with label == X" logic.

        This is optional but makes the code clearer and testable.
        """
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # 3) Nutrition totals aggregation helpers
    # ---------------------------------------------------------------------
    def compute_meal_totals(self, meal_items: Sequence[MealItem]) -> Dict[str, float]:
        """
        Compute nutrition totals needed for effective GL.

        Return a dict such as:
          - total_gl
          - total_fiber_g
          - total_protein_g
          - (optional) total_carbs_g

        Implementation detail:
          - For each meal item:
              features = knowledge_base.get_nutrition_features(food_name, serving_size)
              features contains:
                - glycemic_load
                - fiber
                - protein
                - carbohydrates
              add these to running totals.
        """
        raise NotImplementedError

    def compute_effective_gl(
        self,
        total_gl: float,
        total_fiber_g: float,
        total_protein_g: float,
        *,
        # Suggested step-band thresholds (you choose the exact cutoffs):
        fiber_bands: Tuple[Tuple[float, float], ...] = (
            # (min_inclusive, multiplier)
            (0.0, 1.0),
            (5.0, 0.8),
        ),
        protein_bands: Tuple[Tuple[float, float], ...] = (
            (0.0, 1.0),
            (15.0, 0.8),
        ),
    ) -> EffectiveGLReduction:
        """
        Convert totals into effective GL using fiber/protein reduction.

        Implementation plan:
          1. Determine fiber_multiplier based on total_fiber_g
          2. Determine protein_multiplier based on total_protein_g
          3. effective_gl = total_gl * fiber_multiplier * protein_multiplier
          4. Compute reduction percentages for explanation
          5. Clamp multipliers/effective_gl to reasonable bounds

        Note:
          - For a class project, step bands are typically easier than a
            continuous function and easier to explain in a report.
        """
        raise NotImplementedError

    def classify_meal_by_effective_gl(self, effective_gl: float) -> MealRiskCategory:
        """
        Convert effective GL into meal_risk_category.

        Option A (simple):
          - low: effective_gl <= 10
          - medium: 10 < effective_gl <= 20
          - high: effective_gl > 20

        Option B:
          - You can align directly with Module 2’s thresholds (safe/caution/unsafe)
            then map safe->low, caution->medium, unsafe->high.
        """
        raise NotImplementedError

    def risk_score_from_effective_gl(
        self, effective_gl: float
    ) -> float:
        """
        Convert effective GL into a 0-100 score.

        Suggested approach:
          - Use thresholds for normalization:
              risk_score = min(100, max(0, (effective_gl / 20) * 100))
            or
              piecewise linear by bands.
        """
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # 4) Human-readable explanation helpers
    # ---------------------------------------------------------------------
    def build_contributing_factors(
        self,
        *,
        per_food_results: Sequence[PerFoodSafetyResult],
        label_category: MealRiskCategory,
        total_gl: float,
        total_fiber_g: float,
        total_protein_g: float,
        effective_gl_reduction: Optional[EffectiveGLReduction],
        effective_gl: Optional[float],
        meal_category: MealRiskCategory,
    ) -> List[str]:
        """
        Build list of user-facing reasons (strings).

        Include:
          - counts/summary of safe/caution/unsafe foods (from labels)
          - total GL, total fiber, total protein
          - fiber reduction % and protein reduction %
          - effective GL value and how it maps to meal category
        """
        raise NotImplementedError

    # ---------------------------------------------------------------------
    # 5) Optional: testing/integration-friendly API
    # ---------------------------------------------------------------------
    def analyze_meal_from_precomputed(
        self,
        meal_items: Sequence[MealItem],
        per_food_results: Sequence[PerFoodSafetyResult],
        *,
        precomputed_totals: Optional[Dict[str, float]] = None,
    ) -> MealAnalysisResult:
        """
        Alternative orchestrator for tests:
          - lets tests inject per_food_results and totals
          - avoids calling Module 1/2 in the middle of meal-risk unit tests
        """
        raise NotImplementedError

