"""
Module 5: User feedback + threshold adaptation (Reinforcement Learning).

This package is intentionally a *skeleton* right now: it documents the intended
file structure and public API for Module 5, but does not implement the logic.

High-level intent (from PROPOSAL.md / README.md):
- Accept user feedback about observed blood-sugar outcomes for meals.
- Use RL (Q-learning / policy learning framing) to adapt user-specific thresholds.
- Persist those thresholds so Modules 2–3 can use them in future predictions.

Public API (planned)
- Persistence:
  - load_profile(...)
  - save_profile(...)
- Learning:
  - update_thresholds_from_feedback(...)
  - (optional) apply_feedback_and_persist(...) convenience wrapper

Types
- UserOutcome, Thresholds, RLState, UserProfile, MealRiskCategory, RLAction, ScoreBucket
"""

from .types import (
    MealRiskCategory,
    RLAction,
    RLState,
    ScoreBucket,
    Thresholds,
    UserOutcome,
    UserProfile,
)

__all__ = [
    "MealRiskCategory",
    "RLAction",
    "RLState",
    "ScoreBucket",
    "Thresholds",
    "UserOutcome",
    "UserProfile",
]

