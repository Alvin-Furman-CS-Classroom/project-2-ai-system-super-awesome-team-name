"""Tests for ``src.module5.rl_threshold_adapter`` (incremental)."""

import random
import unittest

from src.module5.rl_threshold_adapter import (
    all_actions,
    apply_action_to_thresholds,
    choose_action,
    derive_state_key,
    q_update,
    reward_from_outcome,
    update_thresholds_from_feedback,
)
from src.module5.user_profile import default_rl_state, default_thresholds


class TestDeriveStateKey(unittest.TestCase):
    def test_buckets(self) -> None:
        self.assertEqual(derive_state_key("low", 0.0), "pred=low|score=0_39")
        self.assertEqual(
            derive_state_key("medium", 39.99), "pred=medium|score=0_39"
        )
        self.assertEqual(
            derive_state_key("high", 40.0), "pred=high|score=40_69"
        )
        self.assertEqual(
            derive_state_key("low", 69.99), "pred=low|score=40_69"
        )
        self.assertEqual(
            derive_state_key("medium", 70.0), "pred=medium|score=70_100"
        )

    def test_clamps_score(self) -> None:
        self.assertIn("score=0_39", derive_state_key("low", -5.0))
        self.assertIn("score=70_100", derive_state_key("low", 200.0))


class TestAllActions(unittest.TestCase):
    def test_count_and_last_is_no_op(self) -> None:
        actions = all_actions()
        self.assertEqual(len(actions), 9)
        self.assertEqual(actions[-1], "no_op")

    def test_order_stable(self) -> None:
        a = all_actions()
        b = all_actions()
        self.assertEqual(a, b)
        self.assertEqual(
            a,
            (
                "inc_safe_gl",
                "dec_safe_gl",
                "inc_caution_gl",
                "dec_caution_gl",
                "inc_safe_gi",
                "dec_safe_gi",
                "inc_caution_gi",
                "dec_caution_gi",
                "no_op",
            ),
        )


class TestChooseAction(unittest.TestCase):
    def test_exploit_picks_highest_q(self) -> None:
        rl = default_rl_state()
        rl["epsilon"] = 0.0
        sk = derive_state_key("medium", 50.0)
        rl["q"][f"{sk}|a=inc_safe_gl"] = 0.5
        rng = random.Random(1)
        self.assertEqual(choose_action(rl, sk, rng), "inc_safe_gl")

    def test_exploit_tie_is_lexicographic_min(self) -> None:
        rl = default_rl_state()
        rl["epsilon"] = 0.0
        sk = "pred=low|score=0_39"
        rng = random.Random(0)
        self.assertEqual(choose_action(rl, sk, rng), "dec_caution_gi")

    def test_explore_is_deterministic_with_seed(self) -> None:
        rl = default_rl_state()
        rl["epsilon"] = 1.0
        sk = derive_state_key("high", 80.0)
        rng = random.Random(42)
        a1 = choose_action(rl, sk, rng)
        rng2 = random.Random(42)
        a2 = choose_action(rl, sk, rng2)
        self.assertEqual(a1, a2)
        self.assertIn(a1, all_actions())


class TestRewardFromOutcome(unittest.TestCase):
    def test_safety_first_miss_spike_penalty_order(self) -> None:
        """Spike after low/medium should hurt more than over-caution (high + no_spike)."""
        low_spike = reward_from_outcome("low", "spike")
        med_spike = reward_from_outcome("medium", "spike")
        high_no = reward_from_outcome("high", "no_spike")
        self.assertLess(low_spike, high_no)
        self.assertLess(med_spike, high_no)
        self.assertLess(low_spike, med_spike)

    def test_aligned_predictions_positive(self) -> None:
        self.assertEqual(reward_from_outcome("low", "no_spike"), 1.0)
        self.assertEqual(reward_from_outcome("high", "spike"), 1.0)

    def test_grid(self) -> None:
        self.assertEqual(reward_from_outcome("low", "mild_spike"), -1.0)
        self.assertEqual(reward_from_outcome("medium", "no_spike"), 0.5)
        self.assertEqual(reward_from_outcome("medium", "mild_spike"), 0.8)
        self.assertEqual(reward_from_outcome("high", "mild_spike"), 0.3)
        self.assertEqual(reward_from_outcome("high", "no_spike"), -0.5)


class TestQUpdate(unittest.TestCase):
    def test_missing_q_starts_at_zero(self) -> None:
        rl = default_rl_state()
        sk = derive_state_key("low", 10.0)
        q_new = q_update(rl, sk, "no_op", 1.0)
        self.assertAlmostEqual(q_new, 0.2)
        self.assertAlmostEqual(rl["q"][f"{sk}|a=no_op"], 0.2)
        self.assertEqual(rl["updates"], 1)

    def test_existing_q_and_formula(self) -> None:
        rl = default_rl_state()
        sk = "pred=medium|score=40_69"
        key = f"{sk}|a=inc_safe_gl"
        rl["q"][key] = 0.5
        q_new = q_update(rl, sk, "inc_safe_gl", 1.0)
        self.assertAlmostEqual(q_new, 0.6)
        self.assertEqual(rl["updates"], 1)


class TestApplyActionToThresholds(unittest.TestCase):
    def test_no_op_is_unchanged(self) -> None:
        base = default_thresholds()
        out = apply_action_to_thresholds(base, "no_op")
        self.assertEqual(out, base)

    def test_does_not_mutate_input(self) -> None:
        base = default_thresholds()
        snapshot = dict(base)
        apply_action_to_thresholds(base, "inc_safe_gl")
        self.assertEqual(base, snapshot)

    def test_inc_safe_gl_step(self) -> None:
        base = default_thresholds()
        out = apply_action_to_thresholds(base, "inc_safe_gl")
        self.assertAlmostEqual(out["safe_gl"], base["safe_gl"] + 0.5)
        self.assertLess(out["safe_gl"], out["caution_gl"])

    def test_enforces_ordering_after_tight_pair(self) -> None:
        tight = {
            "safe_gl": 19.5,
            "caution_gl": 20.0,
            "safe_gi": 55.0,
            "caution_gi": 70.0,
        }
        out = apply_action_to_thresholds(tight, "inc_safe_gl")
        self.assertLess(out["safe_gl"], out["caution_gl"])
        self.assertGreaterEqual(out["caution_gl"] - out["safe_gl"], 0.5)


class TestUpdateThresholdsFromFeedback(unittest.TestCase):
    def test_wires_q_and_thresholds(self) -> None:
        rl = default_rl_state()
        rl["epsilon"] = 0.0
        base = default_thresholds()
        snapshot = dict(base)
        sk = derive_state_key("low", 10.0)
        expected_action = choose_action(rl, sk, random.Random(0))
        new_th, action = update_thresholds_from_feedback(
            base,
            rl,
            "low",
            10.0,
            "no_spike",
            random.Random(0),
        )
        self.assertEqual(action, expected_action)
        self.assertEqual(rl["updates"], 1)
        self.assertEqual(new_th, apply_action_to_thresholds(base, action))
        self.assertEqual(base, snapshot)

    def test_reward_low_no_spike_updates_q(self) -> None:
        rl = default_rl_state()
        rl["epsilon"] = 0.0
        base = default_thresholds()
        sk = derive_state_key("low", 10.0)
        action = choose_action(rl, sk, random.Random(0))
        update_thresholds_from_feedback(
            base, rl, "low", 10.0, "no_spike", random.Random(0)
        )
        key = f"{sk}|a={action}"
        r = reward_from_outcome("low", "no_spike")
        self.assertAlmostEqual(rl["q"][key], rl["alpha"] * r)


if __name__ == "__main__":
    unittest.main()
