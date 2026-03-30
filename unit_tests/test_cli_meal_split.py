"""Tests for CLI meal line splitting (batch meal entry)."""

import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.cli import split_meal_line


class TestSplitMealLine(unittest.TestCase):
    def test_comma_separated(self):
        self.assertEqual(
            split_meal_line("spaghetti, meatballs, tomato sauce"),
            ["spaghetti", "meatballs", "tomato sauce"],
        )

    def test_and_separated(self):
        self.assertEqual(
            split_meal_line("spaghetti and meatballs"),
            ["spaghetti", "meatballs"],
        )

    def test_comma_and_mixed(self):
        self.assertEqual(
            split_meal_line("spaghetti, meatballs and sauce"),
            ["spaghetti", "meatballs", "sauce"],
        )

    def test_compound_phrase_not_split(self):
        self.assertEqual(
            split_meal_line("mac and cheese"),
            ["mac and cheese"],
        )

    def test_compound_case_insensitive(self):
        self.assertEqual(
            split_meal_line("Mac And Cheese"),
            ["Mac And Cheese"],
        )

    def test_empty(self):
        self.assertEqual(split_meal_line(""), [])
        self.assertEqual(split_meal_line("   "), [])

    def test_single_word(self):
        self.assertEqual(split_meal_line("cabbage"), ["cabbage"])


if __name__ == "__main__":
    unittest.main()
