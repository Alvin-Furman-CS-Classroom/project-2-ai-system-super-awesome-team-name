import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure repo root is importable so we can use the `src` package.
# From unit_tests/module3/, two levels up is the repo root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.module3.meal_risk_analyzer import MealRiskAnalyzer


class TestMealRiskAnalyzer(unittest.TestCase):
    def test_compute_effective_gl_step_bands(self):
        # total_gl=30 with high fiber/protein should reduce twice (0.8 * 0.8)
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        reduction = analyzer.compute_effective_gl(
            total_gl=30.0, total_fiber_g=6.0, total_protein_g=16.0
        )

        self.assertAlmostEqual(reduction.fiber_multiplier, 0.8, places=6)
        self.assertAlmostEqual(reduction.protein_multiplier, 0.8, places=6)
        self.assertAlmostEqual(reduction.effective_gl, 19.2, places=6)
        self.assertAlmostEqual(reduction.fiber_reduction_pct, 20.0, places=6)
        self.assertAlmostEqual(reduction.protein_reduction_pct, 20.0, places=6)

    def test_classify_meal_by_effective_gl_thresholds(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        self.assertEqual(analyzer.classify_meal_by_effective_gl(10.0), "low")
        self.assertEqual(analyzer.classify_meal_by_effective_gl(10.1), "medium")
        self.assertEqual(analyzer.classify_meal_by_effective_gl(20.0), "medium")
        self.assertEqual(analyzer.classify_meal_by_effective_gl(20.1), "high")

    def test_effective_gl_can_override_unsafe_label(self):
        # Even if one food is labeled unsafe, effective GL can lower the overall
        # meal risk category when fiber/protein are high enough.
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )

        per_food_results = [
            {"safety_label": "unsafe", "explanation": "High GL"},
            {"safety_label": "safe", "explanation": "Within safe range"},
        ]
        meal_items = [
            {"food_name": "rice", "serving_size": "100g"},
            {"food_name": "salad", "serving_size": "100g"},
        ]

        # Choose totals so effective GL falls into "low":
        # effective_gl = total_gl * 0.8 * 0.8 = total_gl * 0.64
        # For total_gl=15 => 9.6 (<=10) => low.
        precomputed_totals = {
            "total_gl": 15.0,
            "total_fiber_g": 6.0,
            "total_protein_g": 16.0,
        }

        result = analyzer.analyze_meal_from_precomputed(
            meal_items=meal_items,
            per_food_results=per_food_results,  # type: ignore[arg-type]
            precomputed_totals=precomputed_totals,
        )

        self.assertEqual(result["meal_risk_category"], "low")
        self.assertGreaterEqual(result["risk_score"], 0.0)
        self.assertLessEqual(result["risk_score"], 100.0)

    # --- aggregate_from_labels ---

    def test_aggregate_from_labels_all_safe(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        per = [
            {"safety_label": "safe", "explanation": "a"},
            {"safety_label": "safe", "explanation": "b"},
        ]
        cat, score, factors = analyzer.aggregate_from_labels(per)
        self.assertEqual(cat, "low")
        self.assertEqual(score, 0.0)
        self.assertTrue(any("0 unsafe" in f for f in factors))

    def test_aggregate_from_labels_any_unsafe_is_high(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        per = [
            {"safety_label": "safe", "explanation": "a"},
            {"safety_label": "unsafe", "explanation": "b"},
        ]
        cat, score, _ = analyzer.aggregate_from_labels(per)
        self.assertEqual(cat, "high")
        self.assertEqual(score, 50.0)  # 1 unsafe / 2 foods * 100

    def test_aggregate_from_labels_caution_only_is_medium(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        per = [
            {"safety_label": "caution", "explanation": "a"},
            {"safety_label": "caution", "explanation": "b"},
        ]
        cat, score, _ = analyzer.aggregate_from_labels(per)
        self.assertEqual(cat, "medium")
        self.assertEqual(score, 50.0)  # 2 * 0.5 / 2 * 100

    def test_aggregate_from_labels_empty_raises(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        with self.assertRaises(ValueError) as ctx:
            analyzer.aggregate_from_labels([])
        self.assertIn("non-empty", str(ctx.exception).lower())

    # --- analyze_meal validation (mocked Module 1/2) ---

    def test_analyze_meal_empty_raises(self):
        analyzer = MealRiskAnalyzer(MagicMock(), MagicMock(), enable_effective_gl_adjustments=True)
        with self.assertRaises(ValueError) as ctx:
            analyzer.analyze_meal([])
        self.assertIn("non-empty", str(ctx.exception).lower())

    def test_analyze_meal_missing_serving_size_raises(self):
        analyzer = MealRiskAnalyzer(MagicMock(), MagicMock(), enable_effective_gl_adjustments=True)
        with self.assertRaises(ValueError) as ctx:
            analyzer.analyze_meal([{"food_name": "apple"}])
        self.assertIn("Invalid meal item", str(ctx.exception))

    # --- analyze_meal_from_precomputed validation ---

    def test_analyze_meal_from_precomputed_empty_meal_raises(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        with self.assertRaises(ValueError):
            analyzer.analyze_meal_from_precomputed(
                meal_items=[],
                per_food_results=[{"safety_label": "safe", "explanation": "x"}],
            )

    def test_analyze_meal_from_precomputed_empty_per_food_raises(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        with self.assertRaises(ValueError):
            analyzer.analyze_meal_from_precomputed(
                meal_items=[{"food_name": "x", "serving_size": "100g"}],
                per_food_results=[],
            )

    # --- labels-only mode (no effective GL) ---

    def test_labels_only_mode_uses_label_category(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=False,
        )
        result = analyzer.analyze_meal_from_precomputed(
            meal_items=[{"food_name": "a", "serving_size": "100g"}],
            per_food_results=[{"safety_label": "caution", "explanation": "mid"}],
            precomputed_totals={"total_gl": 5.0, "total_fiber_g": 20.0, "total_protein_g": 30.0},
        )
        # Totals ignored when adjustments disabled; category from labels only.
        self.assertEqual(result["meal_risk_category"], "medium")
        # Single caution food: 100 * 0.5 / 1 = 50
        self.assertEqual(result["risk_score"], 50.0)

    # --- compute_effective_gl edge cases ---

    def test_compute_effective_gl_zero_total_gl(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        r = analyzer.compute_effective_gl(0.0, 10.0, 20.0)
        self.assertEqual(r.effective_gl, 0.0)

    def test_fiber_band_boundary_just_below_2g(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        r = analyzer.compute_effective_gl(10.0, 1.99, 0.0)
        self.assertEqual(r.fiber_multiplier, 1.0)
        self.assertAlmostEqual(r.effective_gl, 10.0, places=6)

    def test_fiber_band_boundary_at_2g(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        r = analyzer.compute_effective_gl(10.0, 2.0, 0.0)
        self.assertEqual(r.fiber_multiplier, 0.9)
        self.assertAlmostEqual(r.effective_gl, 9.0, places=6)

    def test_protein_band_boundary_just_below_7g(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        r = analyzer.compute_effective_gl(10.0, 0.0, 6.99)
        self.assertEqual(r.protein_multiplier, 1.0)

    def test_protein_band_boundary_at_7g(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        r = analyzer.compute_effective_gl(10.0, 0.0, 7.0)
        self.assertEqual(r.protein_multiplier, 0.9)

    # --- risk_score_from_effective_gl ---

    def test_risk_score_at_key_boundaries(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        self.assertEqual(analyzer.risk_score_from_effective_gl(0.0), 0.0)
        self.assertAlmostEqual(analyzer.risk_score_from_effective_gl(10.0), 40.0, places=6)
        self.assertAlmostEqual(analyzer.risk_score_from_effective_gl(20.0), 70.0, places=6)

    def test_risk_score_clamps_to_100(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        # Very high effective GL would exceed 100 without clamp
        score = analyzer.risk_score_from_effective_gl(100.0)
        self.assertEqual(score, 100.0)

    # --- build_contributing_factors ---

    def test_build_contributing_factors_note_when_label_differs_from_meal(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        reduction = analyzer.compute_effective_gl(15.0, 6.0, 16.0)
        factors = analyzer.build_contributing_factors(
            per_food_results=[
                {"safety_label": "unsafe", "explanation": "x"},
            ],
            label_category="high",
            total_gl=15.0,
            total_fiber_g=6.0,
            total_protein_g=16.0,
            effective_gl_reduction=reduction,
            effective_gl=reduction.effective_gl,
            meal_category="low",
        )
        self.assertTrue(
            any("individual foods and overall meal" in f for f in factors),
            msg=factors,
        )

    def test_build_contributing_factors_no_note_when_aligned(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        reduction = analyzer.compute_effective_gl(5.0, 6.0, 16.0)
        meal_cat = analyzer.classify_meal_by_effective_gl(reduction.effective_gl)
        factors = analyzer.build_contributing_factors(
            per_food_results=[{"safety_label": "safe", "explanation": "x"}],
            label_category="low",
            total_gl=5.0,
            total_fiber_g=6.0,
            total_protein_g=16.0,
            effective_gl_reduction=reduction,
            effective_gl=reduction.effective_gl,
            meal_category=meal_cat,
        )
        self.assertFalse(
            any("individual foods and overall meal" in f for f in factors),
            msg=factors,
        )

    # --- _exists_label ---

    def test_exists_label(self):
        analyzer = MealRiskAnalyzer(
            knowledge_base=object(),
            food_safety_engine=object(),
            enable_effective_gl_adjustments=True,
        )
        per = [
            {"safety_label": "safe", "explanation": "a"},
            {"safety_label": "unsafe", "explanation": "b"},
        ]
        self.assertTrue(analyzer._exists_label(per, "unsafe"))
        self.assertFalse(analyzer._exists_label(per, "caution"))


if __name__ == "__main__":
    unittest.main()

