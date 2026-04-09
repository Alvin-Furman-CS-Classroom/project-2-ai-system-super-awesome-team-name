"""
User profile persistence (Option A: single JSON file).

Purpose
- Persist one default user's personalization state in a single JSON file.
- Provide safe defaults and resilience: missing/corrupt profile should not break the CLI.

File path (planned)
- data/user_profile.json

Planned JSON schema
{
  "version": 1,
  "thresholds": {
    "safe_gl": 10.0,
    "caution_gl": 20.0,
    "safe_gi": 55.0,
    "caution_gi": 70.0
  },
  "rl_state": {
    "alpha": 0.2,
    "gamma": 0.0,
    "epsilon": 0.1,
    "q": { "pred=medium|score=40_69|a=inc_safe_gl": 0.3 },
    "updates": 17
  },
  "meta": {
    "last_updated_utc": "2026-04-09T20:10:00+00:00"
  }
}

Functions (planned)
- default_profile_path() -> pathlib.Path
    Returns the project-relative path for the JSON profile.

- default_thresholds() -> Thresholds
    Mirrors the current Module 2 safety_rules defaults as a starting point.

- default_rl_state() -> RLState
    Provides starting RL hyperparameters and empty Q-table.

- default_profile() -> UserProfile
    Builds a full default profile including version + meta.

- load_profile(path: Path | None = None) -> UserProfile
    - If missing: return default_profile()
    - If corrupt: return default_profile()
    - If partial: fill missing fields with defaults

- save_profile(profile: UserProfile, path: Path | None = None) -> None
    - Ensure parent directories exist
    - Update meta timestamp
    - Write atomically (temp file then rename) to avoid partial writes

Testing expectations
- deterministic load/save roundtrip
- missing file returns defaults
- malformed JSON returns defaults
- partial schema fills defaults
"""

