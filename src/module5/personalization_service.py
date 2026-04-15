"""
Module 5 convenience service for one feedback event.

Keeps CLI glue minimal by centralizing:
``load_profile -> update_thresholds_from_feedback -> save_profile``.
"""

from __future__ import annotations

from pathlib import Path
from random import Random

from .rl_threshold_adapter import update_thresholds_from_feedback
from .types import MealRiskCategory, UserOutcome, UserProfile
from .user_profile import load_profile, save_profile


def apply_feedback_and_persist(
    *,
    predicted_category: MealRiskCategory,
    predicted_score: float,
    outcome: UserOutcome,
    profile_path: Path | None = None,
    rng: Random | None = None,
) -> UserProfile:
    """
    Apply one user feedback event and persist the updated profile.

    Flow:
    1) Load existing profile (or defaults when missing/corrupt).
    2) Run one RL update from prediction + outcome.
    3) Persist updated thresholds + RL state atomically.
    4) Return the updated profile for caller display/testing.
    """
    profile = load_profile(profile_path)
    new_thresholds, _action = update_thresholds_from_feedback(
        thresholds=profile["thresholds"],
        rl_state=profile["rl_state"],
        predicted_category=predicted_category,
        predicted_score=predicted_score,
        outcome=outcome,
        rng=rng,
    )
    profile["thresholds"] = new_thresholds
    save_profile(profile, profile_path)
    return profile


__all__ = ["apply_feedback_and_persist"]
