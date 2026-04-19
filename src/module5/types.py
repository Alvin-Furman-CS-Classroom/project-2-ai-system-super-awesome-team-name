"""
Module 5 shared types: persisted profile schema and RL vocabulary.

These types mirror `data/user_profile.json` and the Module 5 README contract.
They are TypedDicts so `json.loads` / `json.dumps` round-trips stay straightforward.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# --- Vocabulary aligned with Module 3 meal risk output -----------------------

MealRiskCategory = Literal["low", "medium", "high"]
"""Meal spike-risk tier from the meal-level analyzer (Module 3)."""

UserOutcome = Literal["no_spike", "mild_spike", "spike"]
"""User-reported post-meal glycemic outcome for learning."""

# --- State / action space (threshold RL) ------------------------------------

ScoreBucket = Literal["0_39", "40_69", "70_100"]
"""
Bucket for Module 3 risk score (0–100), used to keep the Q-table small.

Maps to bands: [0, 40), [40, 70), [70, 100] (exact upper-bound policy is
defined in `rl_threshold_adapter.derive_state_key` when implemented).
"""

RLAction = Literal[
    "inc_safe_gl",
    "dec_safe_gl",
    "inc_caution_gl",
    "dec_caution_gl",
    "inc_safe_gi",
    "dec_safe_gi",
    "inc_caution_gi",
    "dec_caution_gi",
    "no_op",
]
"""Discrete threshold nudge chosen by the ε-greedy policy."""


class Thresholds(TypedDict):
    """
    GI/GL cutoffs consumed by Module 2 rules and aligned Module 3 GL bands.

    Invariants (enforced when applying actions, not by the type itself):
    ``safe_gl < caution_gl``, ``safe_gi < caution_gi``.
    """

    safe_gl: float
    caution_gl: float
    safe_gi: float
    caution_gi: float


class RLState(TypedDict):
    """
    Persisted reinforcement-learning state.

    ``q`` maps opaque composite keys (e.g. ``"pred=medium|score=40_69|a=inc_safe_gl"``)
    to scalar action values. Encoding is owned by ``rl_threshold_adapter``.
    """

    alpha: float
    """Learning rate α for the TD/Q update."""

    gamma: float
    """
    Discount γ; use ``0.0`` when each feedback event is treated as terminal
    (README: ``Q ← Q + α (r − Q)`` with no bootstrap from a next state).
    """

    epsilon: float
    """Exploration probability for ε-greedy action selection."""

    q: dict[str, float]
    """Q-values keyed by implementation-defined strings."""

    updates: int
    """Number of Q-updates applied (monotonic counter)."""


class UserProfile(TypedDict):
    """
    Single-document user personalization record (see README Module 5).

    Version allows future migrations of the JSON layout.
    """

    version: int
    thresholds: Thresholds
    rl_state: RLState
    meta: dict[str, str]
    """Arbitrary string metadata (e.g. ``last_updated_utc`` ISO timestamp)."""


__all__ = [
    "MealRiskCategory",
    "RLAction",
    "RLState",
    "ScoreBucket",
    "Thresholds",
    "UserOutcome",
    "UserProfile",
]
