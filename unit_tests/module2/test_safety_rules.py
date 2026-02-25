"""
Unit tests for safety_rules (Module 2): propositional logic for food safety.

Tests get_gl_category, get_gi_category, and evaluate_propositions in isolation
using hand-built feature dicts (no knowledge base).
"""

import unittest
import os
import sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from module2.safety_rules import (
    get_gl_category,
    get_gi_category,
    evaluate_propositions,
    SAFE_GL_THRESHOLD,
    CAUTION_GL_THRESHOLD,
    SAFE_GI_THRESHOLD,
    CAUTION_GI_THRESHOLD,
)


class TestGLCategory(unittest.TestCase):
    """Tests for get_gl_category (glycemic load thresholds)."""

    def test_gl_safe_at_threshold(self):
        """GL exactly at safe threshold is safe."""
        self.assertEqual(get_gl_category(SAFE_GL_THRESHOLD), "safe")

    def test_gl_safe_below_threshold(self):
        """GL below safe threshold is safe."""
        self.assertEqual(get_gl_category(0.0), "safe")
        self.assertEqual(get_gl_category(5.0), "safe")

    def test_gl_caution_above_safe_below_caution(self):
        """GL above safe and at or below caution is caution."""
        self.assertEqual(get_gl_category(10.1), "caution")
        self.assertEqual(get_gl_category(CAUTION_GL_THRESHOLD), "caution")
        self.assertEqual(get_gl_category(15.0), "caution")

    def test_gl_unsafe_above_caution(self):
        """GL above caution threshold is unsafe."""
        self.assertEqual(get_gl_category(20.1), "unsafe")
        self.assertEqual(get_gl_category(50.0), "unsafe")


class TestGICategory(unittest.TestCase):
    """Tests for get_gi_category (glycemic index thresholds)."""

    def test_gi_safe_at_threshold(self):
        """GI exactly at safe threshold is safe."""
        self.assertEqual(get_gi_category(SAFE_GI_THRESHOLD), "safe")

    def test_gi_safe_below_threshold(self):
        """GI below safe threshold is safe."""
        self.assertEqual(get_gi_category(0.0), "safe")
        self.assertEqual(get_gi_category(30.0), "safe")

    def test_gi_caution_above_safe_below_caution(self):
        """GI above safe and at or below caution is caution."""
        self.assertEqual(get_gi_category(55.1), "caution")
        self.assertEqual(get_gi_category(CAUTION_GI_THRESHOLD), "caution")
        self.assertEqual(get_gi_category(65.0), "caution")

    def test_gi_unsafe_above_caution(self):
        """GI above caution threshold is unsafe."""
        self.assertEqual(get_gi_category(70.1), "unsafe")
        self.assertEqual(get_gi_category(90.0), "unsafe")


def _features(gi: float, gl: float) -> dict:
    """Minimal feature dict for evaluate_propositions."""
    return {
        "glycemic_index": gi,
        "glycemic_load": gl,
        "carbohydrates": 0.0,
        "fiber": 0.0,
        "protein": 0.0,
        "fat": 0.0,
        "processing_level": "whole",
        "serving_size_grams": 100.0,
    }


class TestEvaluatePropositions(unittest.TestCase):
    """Tests for evaluate_propositions: label and explanation."""

    def test_label_safe_when_both_safe(self):
        """Both GI and GL safe -> label safe."""
        label, _ = evaluate_propositions(_features(50.0, 8.0))
        self.assertEqual(label, "safe")

    def test_label_caution_when_gl_caution_gi_safe(self):
        """GL caution, GI safe -> label caution."""
        label, _ = evaluate_propositions(_features(50.0, 15.0))
        self.assertEqual(label, "caution")

    def test_label_caution_when_gi_caution_gl_safe(self):
        """GI caution, GL safe -> label caution."""
        label, _ = evaluate_propositions(_features(60.0, 8.0))
        self.assertEqual(label, "caution")

    def test_label_unsafe_when_gl_unsafe(self):
        """GL unsafe -> label unsafe even if GI safe."""
        label, _ = evaluate_propositions(_features(50.0, 25.0))
        self.assertEqual(label, "unsafe")

    def test_label_unsafe_when_gi_unsafe(self):
        """GI unsafe -> label unsafe even if GL safe."""
        label, _ = evaluate_propositions(_features(80.0, 8.0))
        self.assertEqual(label, "unsafe")

    def test_label_unsafe_priority_over_caution(self):
        """If one is unsafe and one caution, label is unsafe."""
        label, _ = evaluate_propositions(_features(75.0, 15.0))
        self.assertEqual(label, "unsafe")

    def test_label_safe_when_zero_gi_and_zero_gl(self):
        """Zero GI and GL are treated as safe."""
        label, explanation = evaluate_propositions(_features(0.0, 0.0))
        self.assertEqual(label, "safe")
        self.assertIn("0.0", explanation)

    def test_explanation_contains_gl_and_gi(self):
        """Explanation mentions both glycemic load and glycemic index."""
        _, explanation = evaluate_propositions(_features(50.0, 8.0))
        self.assertIn("Glycemic load", explanation)
        self.assertIn("Glycemic index", explanation)

    def test_explanation_contains_threshold_values(self):
        """Explanation includes numeric thresholds for clarity (use both in caution range)."""
        # GL=15 and GI=60 so both paragraphs mention safe and caution thresholds
        _, explanation = evaluate_propositions(_features(60.0, 15.0))
        self.assertIn(str(SAFE_GL_THRESHOLD), explanation)
        self.assertIn(str(CAUTION_GL_THRESHOLD), explanation)
        self.assertIn(str(SAFE_GI_THRESHOLD), explanation)
        self.assertIn(str(CAUTION_GI_THRESHOLD), explanation)

    def test_explanation_contains_actual_values(self):
        """Explanation includes the actual GI and GL values used."""
        gi, gl = 60.0, 12.0
        _, explanation = evaluate_propositions(_features(gi, gl))
        self.assertIn("60.0", explanation)
        self.assertIn("12.0", explanation)

    def test_explanation_for_unsafe_gl_and_gi(self):
        """Explanation clearly describes when both GL and GI are unsafe."""
        # Both GL and GI above their caution thresholds
        _, explanation = evaluate_propositions(_features(80.0, 25.0))
        self.assertIn("exceeds caution threshold", explanation)
        self.assertIn(str(CAUTION_GL_THRESHOLD), explanation)
        self.assertIn(str(CAUTION_GI_THRESHOLD), explanation)


if __name__ == "__main__":
    unittest.main()
