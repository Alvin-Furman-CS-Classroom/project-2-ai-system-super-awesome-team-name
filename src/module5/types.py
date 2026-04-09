"""
Module 5 shared types (outline only).

Purpose
- Provide a clean, testable contract for what Module 5 reads/writes.
- Keep typing out of CLI logic and RL logic.

Key types (planned)
- UserOutcome:
    Literal["no_spike", "mild_spike", "spike"]

- Thresholds:
    A dict-like structure containing the personalization knobs that Modules 2–3 use.
    Recommended keys:
      - safe_gl: float
      - caution_gl: float
      - safe_gi: float
      - caution_gi: float

- RLState:
    Minimal persisted RL state so learning continues across runs.
    Recommended fields:
      - alpha: float   (learning rate)
      - gamma: float   (discount factor; can be 0 if treating each feedback as terminal)
      - epsilon: float (exploration probability for epsilon-greedy)
      - q: dict[str, float]  (Q-values keyed by "state|action" encodings)
      - updates: int  (count of Q-updates applied)

- UserProfile:
    Versioned container persisted in a single JSON file.
    Recommended fields:
      - version: int
      - thresholds: Thresholds
      - rl_state: RLState
      - meta: dict[str, str] (e.g., last_updated_utc)

Implementation notes
- Prefer TypedDict or dataclasses for clarity, but keep JSON-serialization simple.
"""

