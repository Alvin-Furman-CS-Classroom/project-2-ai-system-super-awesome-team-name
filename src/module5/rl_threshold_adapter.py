"""
RL threshold adapter (Module 5): map predictions + feedback into threshold tweaks.

Implemented **incrementally**—ask for the next piece when you are ready.

So far
- ``derive_state_key``: coarse RL state string from Module 3 category + score.
- ``all_actions``: fixed ordered list of discrete threshold moves (+ ``no_op``).
- ``choose_action``: ε-greedy pick using ``rl_state["q"]`` and ``rl_state["epsilon"]``.
- ``reward_from_outcome``: safety-first scalar reward from prediction tier + user outcome.
- ``q_update``: one terminal Q-learning step on ``rl_state["q"]`` (+ ``updates`` counter).
- ``apply_action_to_thresholds``: discrete nudge + clamps; keeps ``safe_* < caution_*``.
- ``update_thresholds_from_feedback``: one feedback event → Q-update + new thresholds.
"""

from __future__ import annotations

import random
from typing import Optional, Tuple, cast

from .types import MealRiskCategory, RLAction, RLState, Thresholds, UserOutcome

# Safety-first reward shaping (README Module 5): stronger penalties for missed spikes
# than for being overly cautious when the user reports no spike.
_REWARD_ALIGN: float = 1.0
_REWARD_OK: float = 0.5
_REWARD_MILD_MATCH: float = 0.8
_REWARD_HIGH_MILD: float = 0.3
_PENALTY_OVER_CAUTIOUS: float = -0.5
_PENALTY_LOW_MILD: float = -1.0
_PENALTY_MISS_SPIKE_MEDIUM: float = -2.5
_PENALTY_MISS_SPIKE_LOW: float = -3.0

# Threshold nudges / feasible region (README: small steps, hard clamps, ordering).
_STEP_GL: float = 0.5
_STEP_GI: float = 1.0
_GL_BAND_LO: float = 0.5
_GL_BAND_HI: float = 60.0
_GI_BAND_LO: float = 20.0
_GI_BAND_HI: float = 100.0
_MIN_SEP_GL: float = 0.5
_MIN_SEP_GI: float = 1.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _finalize_gl_pair(safe_gl: float, caution_gl: float) -> tuple[float, float]:
    s = _clamp(safe_gl, _GL_BAND_LO, _GL_BAND_HI)
    c = _clamp(caution_gl, _GL_BAND_LO, _GL_BAND_HI)
    if s + _MIN_SEP_GL > c:
        c = min(_GL_BAND_HI, s + _MIN_SEP_GL)
    if s + _MIN_SEP_GL > c:
        s = max(_GL_BAND_LO, c - _MIN_SEP_GL)
    return s, c


def _finalize_gi_pair(safe_gi: float, caution_gi: float) -> tuple[float, float]:
    s = _clamp(safe_gi, _GI_BAND_LO, _GI_BAND_HI)
    c = _clamp(caution_gi, _GI_BAND_LO, _GI_BAND_HI)
    if s + _MIN_SEP_GI > c:
        c = min(_GI_BAND_HI, s + _MIN_SEP_GI)
    if s + _MIN_SEP_GI > c:
        s = max(_GI_BAND_LO, c - _MIN_SEP_GI)
    return s, c


def derive_state_key(
    predicted_category: MealRiskCategory, predicted_score: float
) -> str:
    """
    Build a small discrete **state** string for the Q-table.

    Uses Module 3's ``low`` / ``medium`` / ``high`` plus a **score bucket** so
    similar predictions share rows: ``0_39``, ``40_69``, ``70_100`` for
    scores in [0, 40), [40, 70), [70, 100] (after clamping to 0–100).
    """
    s = max(0.0, min(100.0, float(predicted_score)))
    if s < 40.0:
        bucket = "0_39"
    elif s < 70.0:
        bucket = "40_69"
    else:
        bucket = "70_100"
    return f"pred={predicted_category}|score={bucket}"


def all_actions() -> tuple[str, ...]:
    """
    Every RL action, in a **fixed order**.

    Order matters for ``choose_action``: when several actions tie on Q-value,
    we break ties lexicographically using this sequence (smallest string wins).
    Names match ``RLAction`` in ``types.py`` and the Module 5 README.
    """
    return (
        "inc_safe_gl",
        "dec_safe_gl",
        "inc_caution_gl",
        "dec_caution_gl",
        "inc_safe_gi",
        "dec_safe_gi",
        "inc_caution_gi",
        "dec_caution_gi",
        "no_op",
    )


def _q_key(state_key: str, action: str) -> str:
    """How we store one Q-value in the flat ``rl_state["q"]`` dict (state + action)."""
    return f"{state_key}|a={action}"


def choose_action(
    rl_state: RLState, state_key: str, rng: Optional[random.Random] = None
) -> str:
    """
    ε-greedy policy.

    With probability ``rl_state["epsilon"]``, return a uniformly random action from
    ``all_actions()``. Otherwise return an action with **highest** Q(state, action),
    using default Q = 0 for missing keys. Ties break by **lexicographically smallest**
    action name (deterministic for tests).
    """
    gen = rng if rng is not None else random.Random()
    actions = all_actions()
    if gen.random() < rl_state["epsilon"]:
        return gen.choice(actions)

    best_val: Optional[float] = None
    best_actions: list[str] = []
    for action in actions:
        qv = rl_state["q"].get(_q_key(state_key, action), 0.0)
        if best_val is None or qv > best_val:
            best_val = qv
            best_actions = [action]
        elif qv == best_val:
            best_actions.append(action)
    return min(best_actions)


def reward_from_outcome(
    predicted_category: MealRiskCategory, outcome: UserOutcome
) -> float:
    """
    Map **prediction tier** + **observed outcome** to a scalar reward for terminal Q-updates.

    Safety-first (README): strong negative reward when the user reports ``spike`` after
    a ``low`` or ``medium`` prediction; a smaller negative reward when the system was
    ``high`` and the user reports ``no_spike`` (over-caution); positive reward when
    the story matches (e.g. ``low`` + ``no_spike``, ``high`` + ``spike``).
    """
    if predicted_category == "low":
        if outcome == "no_spike":
            return _REWARD_ALIGN
        if outcome == "mild_spike":
            return _PENALTY_LOW_MILD
        return _PENALTY_MISS_SPIKE_LOW

    if predicted_category == "medium":
        if outcome == "no_spike":
            return _REWARD_OK
        if outcome == "mild_spike":
            return _REWARD_MILD_MATCH
        return _PENALTY_MISS_SPIKE_MEDIUM

    # predicted_category == "high"
    if outcome == "no_spike":
        return _PENALTY_OVER_CAUTIOUS
    if outcome == "mild_spike":
        return _REWARD_HIGH_MILD
    return _REWARD_ALIGN


def q_update(
    rl_state: RLState,
    state_key: str,
    action: RLAction,
    reward: float,
) -> float:
    """
    Apply one **terminal** Q-learning step (README: ``γ = 0``):

    ``Q(s,a) ← Q(s,a) + α (r − Q(s,a))``

    Missing entries are treated as ``Q = 0`` (same convention as ``choose_action``).
    Writes the new value into ``rl_state["q"]`` and increments ``rl_state["updates"]``.
    Returns the updated ``Q(s,a)``.
    """
    key = _q_key(state_key, action)
    q_old = rl_state["q"].get(key, 0.0)
    alpha = float(rl_state["alpha"])
    r = float(reward)
    q_new = q_old + alpha * (r - q_old)
    rl_state["q"][key] = q_new
    rl_state["updates"] = int(rl_state["updates"]) + 1
    return q_new


def apply_action_to_thresholds(thresholds: Thresholds, action: RLAction) -> Thresholds:
    """
    Return a **new** thresholds dict after applying one discrete RL action.

    ``inc_*`` / ``dec_*`` nudge one cutoff by a small fixed step; ``no_op`` copies inputs.
    Values are clamped to a reasonable band, then ``safe_gl < caution_gl`` and
    ``safe_gi < caution_gi`` are restored if a nudge violated ordering.
    """
    t: dict[str, float] = {
        "safe_gl": float(thresholds["safe_gl"]),
        "caution_gl": float(thresholds["caution_gl"]),
        "safe_gi": float(thresholds["safe_gi"]),
        "caution_gi": float(thresholds["caution_gi"]),
    }

    if action == "inc_safe_gl":
        t["safe_gl"] += _STEP_GL
    elif action == "dec_safe_gl":
        t["safe_gl"] -= _STEP_GL
    elif action == "inc_caution_gl":
        t["caution_gl"] += _STEP_GL
    elif action == "dec_caution_gl":
        t["caution_gl"] -= _STEP_GL
    elif action == "inc_safe_gi":
        t["safe_gi"] += _STEP_GI
    elif action == "dec_safe_gi":
        t["safe_gi"] -= _STEP_GI
    elif action == "inc_caution_gi":
        t["caution_gi"] += _STEP_GI
    elif action == "dec_caution_gi":
        t["caution_gi"] -= _STEP_GI
    elif action == "no_op":
        pass
    else:
        raise ValueError(f"unknown RL action: {action!r}")

    sg, cg = _finalize_gl_pair(t["safe_gl"], t["caution_gl"])
    t["safe_gl"], t["caution_gl"] = sg, cg
    sgi, cgi = _finalize_gi_pair(t["safe_gi"], t["caution_gi"])
    t["safe_gi"], t["caution_gi"] = sgi, cgi

    out: Thresholds = {
        "safe_gl": t["safe_gl"],
        "caution_gl": t["caution_gl"],
        "safe_gi": t["safe_gi"],
        "caution_gi": t["caution_gi"],
    }
    return out


def update_thresholds_from_feedback(
    thresholds: Thresholds,
    rl_state: RLState,
    predicted_category: MealRiskCategory,
    predicted_score: float,
    outcome: UserOutcome,
    rng: Optional[random.Random] = None,
) -> Tuple[Thresholds, RLAction]:
    """
    Run one learning step from Module 3 prediction context + user outcome.

    Builds ``state_key``, computes reward, picks an action with ``choose_action``,
    applies a terminal ``q_update`` for ``(state_key, action)``, then returns
    updated thresholds from ``apply_action_to_thresholds``. Mutates ``rl_state``
    (Q-table + ``updates``); does not mutate ``thresholds``.
    """
    state_key = derive_state_key(predicted_category, predicted_score)
    reward = reward_from_outcome(predicted_category, outcome)
    action = cast(RLAction, choose_action(rl_state, state_key, rng))
    q_update(rl_state, state_key, action, reward)
    new_thresholds = apply_action_to_thresholds(thresholds, action)
    return new_thresholds, action


__all__ = [
    "all_actions",
    "apply_action_to_thresholds",
    "choose_action",
    "derive_state_key",
    "q_update",
    "reward_from_outcome",
    "update_thresholds_from_feedback",
]
