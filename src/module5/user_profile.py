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
    If missing, corrupt JSON, or wrong top-level type: return default_profile().
    If partial: merge recognized fields onto defaults.

- save_profile(profile: UserProfile, path: Path | None = None) -> None
    Ensures parent dirs exist, sets meta.last_updated_utc, writes JSON via temp + replace.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .types import RLState, Thresholds, UserProfile
from src.module2.safety_rules import (
    CAUTION_GL_THRESHOLD,
    CAUTION_GI_THRESHOLD,
    SAFE_GL_THRESHOLD,
    SAFE_GI_THRESHOLD,
)

# finding the path to the json file by backtracking to the root of the repo and then locating the data folder
def default_profile_path() -> Path:
    """Return ``<repo>/data/user_profile.json`` regardless of the process cwd."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "data" / "user_profile.json"


def default_thresholds() -> Thresholds:
    """Return GI/GL cutoffs matching ``src.module2.safety_rules`` defaults."""
    return {
        "safe_gl": SAFE_GL_THRESHOLD,
        "caution_gl": CAUTION_GL_THRESHOLD,
        "safe_gi": SAFE_GI_THRESHOLD,
        "caution_gi": CAUTION_GI_THRESHOLD,
    }


def default_rl_state() -> RLState:
    """Return fresh RL hyperparameters and an empty Q-table (matches README defaults)."""
    return {
        "alpha": 0.2,
        "gamma": 0.0,
        "epsilon": 0.1,
        "q": {},
        "updates": 0,
    }


def default_profile() -> UserProfile:
    """Return a new in-memory profile: schema version 1, default thresholds and RL state."""
    return {
        "version": 1,
        "thresholds": default_thresholds(),
        "rl_state": default_rl_state(),
        "meta": {},
    }


def load_profile(path: Path | None = None) -> UserProfile:
    """Load JSON from disk, or return defaults when the file is unusable."""
    resolved = path if path is not None else default_profile_path()
    if not resolved.is_file():
        return default_profile()
    try:
        text = resolved.read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default_profile()
    if not isinstance(payload, dict):
        return default_profile()
    return _merge_profile_payload(payload)


def _finite_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
        if out != out or out in (float("inf"), float("-inf")):  # NaN / inf
            return None
        return out
    return None


def _positive_int_version(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 1:
        return value
    if isinstance(value, float) and value.is_integer():
        iv = int(value)
        if iv >= 1:
            return iv
    return None


def _non_negative_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer():
        iv = int(value)
        if iv >= 0:
            return iv
    return None


def _merge_thresholds(raw: Any) -> Thresholds:
    base = default_thresholds()
    if not isinstance(raw, dict):
        return base
    out: Thresholds = dict(base)
    for key in ("safe_gl", "caution_gl", "safe_gi", "caution_gi"):
        if key not in raw:
            continue
        parsed = _finite_float(raw[key])
        if parsed is not None:
            out[key] = parsed
    return out


def _merge_rl_state(raw: Any) -> RLState:
    base = default_rl_state()
    if not isinstance(raw, dict):
        return base
    out: RLState = {**base, "q": dict(base["q"])}
    for name in ("alpha", "gamma", "epsilon"):
        if name not in raw:
            continue
        parsed = _finite_float(raw[name])
        if parsed is not None:
            out[name] = parsed
    if "updates" in raw:
        u = _non_negative_int(raw["updates"])
        if u is not None:
            out["updates"] = u
    if "q" in raw and isinstance(raw["q"], dict):
        q_clean: dict[str, float] = {}
        for k, v in raw["q"].items():
            if not isinstance(k, str):
                continue
            fv = _finite_float(v)
            if fv is not None:
                q_clean[k] = fv
        out["q"] = q_clean
    return out


def _merge_meta(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(k, str):
            out[k] = str(v)
    return out


def _merge_profile_payload(raw: Mapping[str, Any]) -> UserProfile:
    defaults = default_profile()
    version = _positive_int_version(raw.get("version"))
    if version is None:
        version = defaults["version"]
    return {
        "version": version,
        "thresholds": _merge_thresholds(raw.get("thresholds")),
        "rl_state": _merge_rl_state(raw.get("rl_state")),
        "meta": _merge_meta(raw.get("meta")),
    }


def save_profile(profile: UserProfile, path: Path | None = None) -> None:
    """Write ``profile`` to JSON; does not mutate the caller's ``profile`` dict."""
    resolved = path if path is not None else default_profile_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    meta = dict(profile.get("meta", {}))
    meta["last_updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rl = profile["rl_state"]
    payload = {
        "version": profile["version"],
        "thresholds": dict(profile["thresholds"]),
        "rl_state": {
            "alpha": rl["alpha"],
            "gamma": rl["gamma"],
            "epsilon": rl["epsilon"],
            "q": dict(rl["q"]),
            "updates": rl["updates"],
        },
        "meta": meta,
    }

    fd, tmp_name = tempfile.mkstemp(
        prefix=".user_profile.",
        suffix=".tmp",
        dir=str(resolved.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_path, resolved)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


# --- Testing expectations (manual / future unit tests) ---------------------
# - deterministic load/save roundtrip
# - missing file returns defaults
# - malformed JSON returns defaults
# - partial schema fills defaults
