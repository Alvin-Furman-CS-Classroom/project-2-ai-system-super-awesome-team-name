import os
import unittest
import sys

# Ensure repo root is importable so we can use the `src` package.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..", ".."))
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


if __name__ == "__main__":
    unittest.main()

