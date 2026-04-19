import json
import tempfile
import unittest
from pathlib import Path

from src.module5.user_profile import default_profile, load_profile, save_profile


class TestUserProfilePersistence(unittest.TestCase):
    def test_load_missing_file_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "missing.json"
            profile = load_profile(profile_path)
            self.assertEqual(profile["version"], 1)
            self.assertIn("safe_gl", profile["thresholds"])

    def test_load_corrupt_json_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "user_profile.json"
            profile_path.write_text("{not-valid-json", encoding="utf-8")
            profile = load_profile(profile_path)
            self.assertEqual(profile["version"], 1)
            self.assertEqual(profile["rl_state"]["updates"], 0)

    def test_save_then_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "user_profile.json"
            profile = default_profile()
            profile["thresholds"]["safe_gl"] = 9.5
            profile["rl_state"]["updates"] = 7
            profile["meta"]["note"] = "unit-test"

            save_profile(profile, profile_path)
            loaded = load_profile(profile_path)

            self.assertEqual(loaded["thresholds"]["safe_gl"], 9.5)
            self.assertEqual(loaded["rl_state"]["updates"], 7)
            self.assertEqual(loaded["meta"]["note"], "unit-test")
            self.assertIn("last_updated_utc", loaded["meta"])

    def test_load_partial_payload_merges_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "user_profile.json"
            payload = {
                "version": 1,
                "thresholds": {"safe_gl": 9.0},
                "rl_state": {"alpha": 0.3, "q": {"x": 1.0}},
                "meta": {"source": "partial"},
            }
            profile_path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_profile(profile_path)

            self.assertEqual(loaded["thresholds"]["safe_gl"], 9.0)
            self.assertIn("caution_gl", loaded["thresholds"])
            self.assertEqual(loaded["rl_state"]["alpha"], 0.3)
            self.assertEqual(loaded["meta"]["source"], "partial")


if __name__ == "__main__":
    unittest.main()
