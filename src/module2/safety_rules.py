"""
Safety Rules: Propositional logic rules for evaluating food safety.

Defines thresholds and proposition evaluation functions for determining
blood-sugar safety labels (safe/caution/unsafe) based on nutrition features.

Thresholds follow common clinical-style GI/GL groupings:
- Glycemic load: low (≤10), medium (11–19), high (≥20)
- Glycemic index: low (≤55), medium (56–69), high (≥70)

Created 2/3/2026
Authors: Jia Lin and Della Avent
"""

from typing import Dict, Mapping, Tuple, TypedDict


class NutritionFeatures(TypedDict):
    """Typed view of the nutrition features dict supplied by Module 1."""

    glycemic_index: float
    glycemic_load: float
    carbohydrates: float
    fiber: float
    protein: float
    fat: float
    processing_level: str
    serving_size_grams: float


# Default thresholds for glycemic load (GL)
SAFE_GL_THRESHOLD = 10.0      # GL <= 10 is safe
CAUTION_GL_THRESHOLD = 20.0   # GL > 10 and < 20 is caution
# GL >= 20 is unsafe

# Default thresholds for glycemic index (GI)
SAFE_GI_THRESHOLD = 55.0       # GI <= 55 is safe
CAUTION_GI_THRESHOLD = 70.0    # GI > 55 and < 70 is caution
# GI >= 70 is unsafe

# Additional rules based on processing level (e.g., ultra-processed foods)
# can be layered on top of these thresholds in future iterations if needed
# by downstream modules. For Checkpoint 2, we focus on transparent GI/GL rules.


def _resolve_thresholds(
    thresholds: Mapping[str, float] | None,
) -> tuple[float, float, float, float]:
    """Resolve active thresholds, falling back to module defaults when omitted."""
    if thresholds is None:
        return (
            SAFE_GL_THRESHOLD,
            CAUTION_GL_THRESHOLD,
            SAFE_GI_THRESHOLD,
            CAUTION_GI_THRESHOLD,
        )
    return (
        float(thresholds.get("safe_gl", SAFE_GL_THRESHOLD)),
        float(thresholds.get("caution_gl", CAUTION_GL_THRESHOLD)),
        float(thresholds.get("safe_gi", SAFE_GI_THRESHOLD)),
        float(thresholds.get("caution_gi", CAUTION_GI_THRESHOLD)),
    )


def get_gl_category(
    glycemic_load: float,
    *,
    safe_gl_threshold: float = SAFE_GL_THRESHOLD,
    caution_gl_threshold: float = CAUTION_GL_THRESHOLD,
) -> str:
    """Determine safety category based on glycemic load.
    
    Args:
        glycemic_load: Glycemic load value.
    
    Returns:
        "safe" if GL <= SAFE_GL_THRESHOLD,
        "caution" if GL > SAFE_GL_THRESHOLD and <= CAUTION_GL_THRESHOLD,
        "unsafe" if GL > CAUTION_GL_THRESHOLD.
    """
    if glycemic_load <= safe_gl_threshold:
        return "safe"
    if glycemic_load <= caution_gl_threshold:
        return "caution"
    return "unsafe"


def get_gi_category(
    glycemic_index: float,
    *,
    safe_gi_threshold: float = SAFE_GI_THRESHOLD,
    caution_gi_threshold: float = CAUTION_GI_THRESHOLD,
) -> str:
    """Determine safety category based on glycemic index.
    
    Args:
        glycemic_index: Glycemic index value.
    
    Returns:
        "safe" if GI <= SAFE_GI_THRESHOLD,
        "caution" if GI > SAFE_GI_THRESHOLD and <= CAUTION_GI_THRESHOLD,
        "unsafe" if GI > CAUTION_GI_THRESHOLD.
    """
    if glycemic_index <= safe_gi_threshold:
        return "safe"
    if glycemic_index <= caution_gi_threshold:
        return "caution"
    return "unsafe"


def _build_explanation(
    gl: float,
    gi: float,
    *,
    safe_gl_threshold: float,
    caution_gl_threshold: float,
    safe_gi_threshold: float,
    caution_gi_threshold: float,
) -> str:
    """Build a human-readable explanation for the given GL and GI values."""
    parts = []
    if gl <= safe_gl_threshold:
        parts.append(f"Glycemic load {gl:.1f} within safe range (≤{safe_gl_threshold}).")
    elif gl <= caution_gl_threshold:
        parts.append(
            f"Glycemic load {gl:.1f} exceeds safe threshold ({safe_gl_threshold}); "
            f"within caution range (≤{caution_gl_threshold})."
        )
    else:
        parts.append(f"Glycemic load {gl:.1f} exceeds caution threshold ({caution_gl_threshold}).")

    if gi <= safe_gi_threshold:
        parts.append(f"Glycemic index {gi:.1f} within safe range (≤{safe_gi_threshold}).")
    elif gi <= caution_gi_threshold:
        parts.append(
            f"Glycemic index {gi:.1f} exceeds safe threshold ({safe_gi_threshold}); "
            f"within caution range (≤{caution_gi_threshold})."
        )
    else:
        parts.append(f"Glycemic index {gi:.1f} exceeds caution threshold ({caution_gi_threshold}).")

    return " ".join(parts)


def evaluate_propositions(
    features: NutritionFeatures,
    thresholds: Mapping[str, float] | None = None,
) -> Tuple[str, str]:
    """Evaluate all propositional rules against nutrition features.
    
    Args:
        features: Dict from Module 1 with keys: glycemic_index, glycemic_load,
                 carbohydrates, fiber, protein, fat, processing_level, serving_size_grams.
    
    Returns:
        Tuple of (safety_label, explanation) where:
        - safety_label: "safe", "caution", or "unsafe"
        - explanation: Human-readable explanation of which rules fired
    
    Note:
        Priority: unsafe > caution > safe (if multiple rules fire, use highest priority).
    """
    gl = features["glycemic_load"]
    gi = features["glycemic_index"]
    safe_gl_threshold, caution_gl_threshold, safe_gi_threshold, caution_gi_threshold = _resolve_thresholds(
        thresholds
    )
    gl_cat = get_gl_category(
        gl,
        safe_gl_threshold=safe_gl_threshold,
        caution_gl_threshold=caution_gl_threshold,
    )
    gi_cat = get_gi_category(
        gi,
        safe_gi_threshold=safe_gi_threshold,
        caution_gi_threshold=caution_gi_threshold,
    )

    if gl_cat == "unsafe" or gi_cat == "unsafe":
        label = "unsafe"
    elif gl_cat == "caution" or gi_cat == "caution":
        label = "caution"
    else:
        label = "safe"

    explanation = _build_explanation(
        gl,
        gi,
        safe_gl_threshold=safe_gl_threshold,
        caution_gl_threshold=caution_gl_threshold,
        safe_gi_threshold=safe_gi_threshold,
        caution_gi_threshold=caution_gi_threshold,
    )
    return (label, explanation)
