"""
Optional convenience wrapper (outline only).

Purpose
- Keep CLI glue minimal by centralizing:
  load_profile -> update_thresholds_from_feedback -> save_profile

Planned function
- apply_feedback_and_persist(
      *,
      predicted_category: MealRiskCategory,
      predicted_score: float,
      outcome: UserOutcome,
      profile_path: Path | None = None,
      rng: Random | None = None,
  ) -> UserProfile

Behavior (planned)
- Load existing profile (or defaults).
- Compute updated thresholds + RL state (Q-learning update).
- Save the updated profile back to JSON.
- Return the updated profile (for CLI display / testing).
"""

