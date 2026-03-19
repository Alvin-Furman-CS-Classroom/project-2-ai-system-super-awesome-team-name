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
        if not meal_items:
            raise ValueError("meal_items must be a non-empty list.")

        for idx, item in enumerate(meal_items):
            if "food_name" not in item or "serving_size" not in item:
                raise ValueError(f"Invalid meal item at index {idx}: {item!r}")

        per_food_results: List[PerFoodSafetyResult] = []
        for item in meal_items:
            label_result = self.food_safety_engine.evaluate_food(
                item["food_name"], item["serving_size"]
            )
            # normalize keys to the schema used by this module
            per_food_results.append(
                PerFoodSafetyResult(
                    safety_label=label_result["safety_label"],  # type: ignore[arg-type]
                    explanation=label_result["explanation"],  # type: ignore[arg-type]
                )
            )

        label_category, label_score, label_factors = self.aggregate_from_labels(
            per_food_results
        )

        if not self.enable_effective_gl_adjustments:
            return MealAnalysisResult(
                meal_risk_category=label_category,
                risk_score=label_score,
                contributing_factors=label_factors,
            )

        totals = self.compute_meal_totals(meal_items)
        total_gl = totals["total_gl"]
        total_fiber_g = totals["total_fiber_g"]
        total_protein_g = totals["total_protein_g"]

        reduction = self.compute_effective_gl(total_gl, total_fiber_g, total_protein_g)
        effective_gl = reduction.effective_gl

        meal_category = self.classify_meal_by_effective_gl(effective_gl)
        score = self.risk_score_from_effective_gl(effective_gl)

        factors = self.build_contributing_factors(
            per_food_results=per_food_results,
            label_category=label_category,
            total_gl=total_gl,
            total_fiber_g=total_fiber_g,
            total_protein_g=total_protein_g,
            effective_gl_reduction=reduction,
            effective_gl=effective_gl,
            meal_category=meal_category,
        )

        return MealAnalysisResult(
            meal_risk_category=meal_category,
            risk_score=score,
            contributing_factors=factors,
        )

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
        if not per_food_results:
            raise ValueError("per_food_results must be non-empty.")

        unsafe_count = sum(1 for r in per_food_results if r["safety_label"] == "unsafe")
        caution_count = sum(1 for r in per_food_results if r["safety_label"] == "caution")
        safe_count = len(per_food_results) - unsafe_count - caution_count

        if unsafe_count > 0:
            category: MealRiskCategory = "high"
        elif caution_count > 0:
            category = "medium"
        else:
            category = "low"

        # Simple count-based score:
        # unsafe = 1.0, caution = 0.5, safe = 0.0, normalized by meal size.
        meal_size = max(1, len(per_food_results))
        risk_score = 100.0 * (unsafe_count * 1.0 + caution_count * 0.5) / meal_size

        factors: List[str] = [
            f"Per-food safety labels: {unsafe_count} unsafe, {caution_count} caution, {safe_count} safe."
        ]
        factors.append(
            f"Meal categorized as {category.replace('low', 'low spike risk').replace('medium', 'medium spike risk').replace('high', 'high spike risk')}"
        )
        return category, float(risk_score), factors

    def _exists_label(
        self,
        per_food_results: Sequence[PerFoodSafetyResult],
        label: FoodSafetyLabel,
    ) -> bool:
        """
        Helper for FOL-like "exists food with label == X" logic.

        This is optional but makes the code clearer and testable.
        """
        return any(r["safety_label"] == label for r in per_food_results)

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
        if not meal_items:
            raise ValueError("meal_items must be non-empty to compute totals.")

        total_gl = 0.0
        total_fiber_g = 0.0
        total_protein_g = 0.0

        for item in meal_items:
            features = self.knowledge_base.get_nutrition_features(
                item["food_name"], item["serving_size"]
            )
            total_gl += float(features["glycemic_load"])
            total_fiber_g += float(features["fiber"])
            total_protein_g += float(features["protein"])

        return {
            "total_gl": total_gl,
            "total_fiber_g": total_fiber_g,
            "total_protein_g": total_protein_g,
        }

    def compute_effective_gl(
        self,
        total_gl: float,
        total_fiber_g: float,
        total_protein_g: float,
        *,
        # Suggested step-band thresholds (you choose the exact cutoffs):
        fiber_bands: Tuple[Tuple[float, float], ...] = (
            # (min_inclusive, multiplier)
            # <2g -> 1.0
            # 2-4.9g -> 0.9
            # >=5g -> 0.8
            (0.0, 1.0),
            (2.0, 0.9),
            (5.0, 0.8),
        ),
        protein_bands: Tuple[Tuple[float, float], ...] = (
            # <7g -> 1.0
            # 7-14.9g -> 0.9
            # >=15g -> 0.8
            (0.0, 1.0),
            (7.0, 0.9),
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
        def multiplier_from_bands(value_g: float, bands: Tuple[Tuple[float, float], ...]) -> float:
            # Pick the band with the highest min_inclusive that is <= value_g
            # Example: bands [(0,1),(5,0.8)] => value 6 -> 0.8, value 2 -> 1.0.
            selected_multiplier = 1.0
            selected_min = -1.0
            for min_inclusive, multiplier in bands:
                if value_g >= min_inclusive and min_inclusive >= selected_min:
                    selected_min = min_inclusive
                    selected_multiplier = multiplier
            return float(selected_multiplier)

        fiber_multiplier = multiplier_from_bands(total_fiber_g, fiber_bands)
        protein_multiplier = multiplier_from_bands(total_protein_g, protein_bands)

        # Clamp multipliers to a reasonable range to avoid negative/overshooting.
        fiber_multiplier = max(0.0, min(1.0, fiber_multiplier))
        protein_multiplier = max(0.0, min(1.0, protein_multiplier))

        total_gl = max(0.0, float(total_gl))
        effective_gl = total_gl * fiber_multiplier * protein_multiplier

        fiber_reduction_pct = (1.0 - fiber_multiplier) * 100.0
        protein_reduction_pct = (1.0 - protein_multiplier) * 100.0

        return EffectiveGLReduction(
            fiber_multiplier=fiber_multiplier,
            protein_multiplier=protein_multiplier,
            effective_gl=effective_gl,
            fiber_reduction_pct=fiber_reduction_pct,
            protein_reduction_pct=protein_reduction_pct,
        )

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
        effective_gl = float(effective_gl)

        # Module 2 GL thresholds are:
        # - safe: GL <= 10.0
        # - caution: GL > 10.0 and <= 20.0
        # - unsafe: GL > 20.0
        if effective_gl <= 10.0:
            return "low"
        if effective_gl <= 20.0:
            return "medium"
        return "high"

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
        effective_gl = float(effective_gl)
        if effective_gl <= 10.0:
            # 0..10 maps to 0..40
            score = (effective_gl / 10.0) * 40.0
        elif effective_gl <= 20.0:
            # 10..20 maps to 40..70
            score = 40.0 + ((effective_gl - 10.0) / 10.0) * 30.0
        else:
            # >20 maps to 70..100 with a gentler slope
            score = 70.0 + ((effective_gl - 20.0) / 20.0) * 30.0

        return float(max(0.0, min(100.0, score)))

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
        unsafe_count = sum(1 for r in per_food_results if r["safety_label"] == "unsafe")
        caution_count = sum(1 for r in per_food_results if r["safety_label"] == "caution")
        safe_count = len(per_food_results) - unsafe_count - caution_count

        factors: List[str] = []

        # Lead with final meal-level conclusion first to avoid confusion.
        readable_category = {
            "low": "low",
            "medium": "medium",
            "high": "high",
        }[meal_category]

        if effective_gl is not None and effective_gl_reduction is not None:
            factors.append(
                f"Final meal risk is {readable_category} (final sugar-impact score: {effective_gl:.1f})."
            )
            factors.append(
                f"Before balancing effects, your meal's sugar-impact score was {total_gl:.1f}."
            )
            factors.append(
                f"This meal has {total_fiber_g:.1f}g of fiber and {total_protein_g:.1f}g of protein."
            )
            factors.append(
                f"Fiber lowers the sugar impact by about {effective_gl_reduction.fiber_reduction_pct:.0f}%."
            )
            factors.append(
                f"Protein lowers the sugar impact by about {effective_gl_reduction.protein_reduction_pct:.0f}%."
            )

            if label_category != meal_category:
                factors.append(
                    "Note: individual foods and overall meal can differ because meal-level risk uses the full meal together."
                )
        else:
            factors.append(f"Final meal risk is {readable_category}.")

        # Keep wording simple and concrete for broad audiences.
        food_level_parts: List[str] = []
        if unsafe_count > 0:
            food_level_parts.append(f"{unsafe_count} high-risk")
        if caution_count > 0:
            food_level_parts.append(f"{caution_count} medium-risk")
        if safe_count > 0:
            food_level_parts.append(f"{safe_count} lower-risk")
        if food_level_parts:
            factors.append(
                "At the individual-food level: " + ", ".join(food_level_parts) + " food(s)."
            )

        return factors

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
        if not meal_items:
            raise ValueError("meal_items must be non-empty.")
        if not per_food_results:
            raise ValueError("per_food_results must be non-empty.")

        label_category, label_score, label_factors = self.aggregate_from_labels(
            per_food_results
        )

        if not self.enable_effective_gl_adjustments:
            return MealAnalysisResult(
                meal_risk_category=label_category,
                risk_score=label_score,
                contributing_factors=label_factors,
            )

        if precomputed_totals is not None:
            totals = precomputed_totals
        else:
            totals = self.compute_meal_totals(meal_items)

        total_gl = float(totals["total_gl"])
        total_fiber_g = float(totals["total_fiber_g"])
        total_protein_g = float(totals["total_protein_g"])

        reduction = self.compute_effective_gl(total_gl, total_fiber_g, total_protein_g)
        effective_gl = reduction.effective_gl

        meal_category = self.classify_meal_by_effective_gl(effective_gl)
        score = self.risk_score_from_effective_gl(effective_gl)

        factors = self.build_contributing_factors(
            per_food_results=per_food_results,
            label_category=label_category,
            total_gl=total_gl,
            total_fiber_g=total_fiber_g,
            total_protein_g=total_protein_g,
            effective_gl_reduction=reduction,
            effective_gl=effective_gl,
            meal_category=meal_category,
        )

        return MealAnalysisResult(
            meal_risk_category=meal_category,
            risk_score=score,
            contributing_factors=factors,
        )

