"""
RL threshold adapter (Q-learning / policy learning) — outline only.

Purpose
- Convert user feedback about meal outcomes into small threshold adjustments.
- Demonstrate RL concepts (state/action/reward/Q-update) in a checkpoint-friendly way.

Inputs at feedback time (planned)
- predicted_category: "low" | "medium" | "high"   (from Module 3)
- predicted_score: float (0–100)                 (from Module 3)
- outcome: "no_spike" | "mild_spike" | "spike"  (user-provided)
- current thresholds + rl_state (from user_profile.json)

State representation (planned)
- Derive a *coarse* state key based on the system's prediction, e.g.:
  - predicted category
  - predicted score bucket: 0–39 / 40–69 / 70–100
Example state key: "pred=medium|score=40_69"

Action space (planned)
- Discrete threshold moves (small step sizes), e.g.:
  - inc_safe_gl / dec_safe_gl
  - inc_caution_gl / dec_caution_gl
  - inc_safe_gi / dec_safe_gi
  - inc_caution_gi / dec_caution_gi
  - no_op

Reward shaping (planned)
- Correct prediction category vs observed outcome => positive reward.
- Under-prediction (predicted low/medium, but spike occurred) => larger penalty.
- Over-prediction (predicted high, but no spike) => smaller penalty (safety-first bias).

Learning rule (planned)
- Epsilon-greedy policy for action selection:
  - with prob epsilon: explore random action
  - else: exploit argmax_a Q(s,a)

- Q-learning update:
  - If treating each feedback event as terminal:
      Q(s,a) <- Q(s,a) + alpha * (reward - Q(s,a))
    (Simple, deterministic, easy to test while still being “standard Q-learning”.)

Threshold application + invariants (planned)
- Clamp into safe ranges (example):
  - GL: >= 1, <= 60 (safe) / <= 80 (caution)
  - GI: >= 1, <= 100
- Maintain ordering:
  - safe_gl < caution_gl
  - safe_gi < caution_gi
- Use small step sizes (e.g., 1.0 or 2.0) to avoid extreme drift.

Functions (planned)
- derive_state_key(predicted_category: MealRiskCategory, predicted_score: float) -> str
- all_actions() -> tuple[str, ...]
- choose_action(rl_state: RLState, state_key: str, rng: Random | None = None) -> str
- reward_from_outcome(predicted_category: MealRiskCategory, outcome: UserOutcome) -> float
- q_update(...): update rl_state["q"] in-place
- apply_action_to_thresholds(thresholds: Thresholds, action: str) -> Thresholds
- update_thresholds_from_feedback(...) -> (new_thresholds, action_taken, reward)

Testing expectations
- deterministic action selection and Q-update with fixed RNG seed
- invariants always hold after applying actions
"""

