import tempfile
import unittest
from pathlib import Path

from src.module5.personalization_service import apply_feedback_and_persist
from src.module5.user_profile import default_profile, load_profile, save_profile


class TestPersonalizationService(unittest.TestCase):
    def test_apply_feedback_updates_rl_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "user_profile.json"
            seed = default_profile()
            seed["rl_state"]["epsilon"] = 0.0
            state_key = "pred=low|score=0_39"
            seed["rl_state"]["q"][f"{state_key}|a=no_op"] = 5.0
            save_profile(seed, profile_path)

            updated = apply_feedback_and_persist(
                predicted_category="low",
                predicted_score=10.0,
                outcome="no_spike",
                profile_path=profile_path,
            )

            # no_op stays selected because it's pre-seeded as best action.
            self.assertEqual(updated["thresholds"], seed["thresholds"])
            self.assertEqual(updated["rl_state"]["updates"], seed["rl_state"]["updates"] + 1)

            loaded = load_profile(profile_path)
            self.assertEqual(loaded["rl_state"]["updates"], updated["rl_state"]["updates"])
            self.assertEqual(loaded["thresholds"], updated["thresholds"])

    def test_apply_feedback_creates_profile_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "new_profile.json"
            updated = apply_feedback_and_persist(
                predicted_category="medium",
                predicted_score=45.0,
                outcome="mild_spike",
                profile_path=profile_path,
            )
            self.assertTrue(profile_path.exists())
            self.assertGreaterEqual(updated["rl_state"]["updates"], 1)


if __name__ == "__main__":
    unittest.main()
