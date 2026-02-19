"""
Safety Rules: Propositional logic rules for evaluating food safety.

Defines thresholds and proposition evaluation functions for determining
blood-sugar safety labels (safe/caution/unsafe) based on nutrition features.

Created 2/3/2026
Authors: Jia Lin and Della Avent
"""

from typing import Dict, Tuple

# Default thresholds for glycemic load (GL)
SAFE_GL_THRESHOLD = 10.0      # GL <= 10 is safe
CAUTION_GL_THRESHOLD = 20.0   # GL > 10 and < 20 is caution
# GL >= 20 is unsafe

# Default thresholds for glycemic index (GI)
SAFE_GI_THRESHOLD = 55.0       # GI <= 55 is safe
CAUTION_GI_THRESHOLD = 70.0    # GI > 55 and < 70 is caution
# GI >= 70 is unsafe

# TODO: Add processing level rules if needed
# TODO: Document threshold sources/rationale (e.g., clinical guidelines)


def get_gl_category(glycemic_load: float) -> str:
    """Determine safety category based on glycemic load.
    
    Args:
        glycemic_load: Glycemic load value.
    
    Returns:
        "safe" if GL <= SAFE_GL_THRESHOLD,
        "caution" if GL > SAFE_GL_THRESHOLD and <= CAUTION_GL_THRESHOLD,
        "unsafe" if GL > CAUTION_GL_THRESHOLD.
    """
    if glycemic_load <= SAFE_GL_THRESHOLD:
        return "safe"
    if glycemic_load <= CAUTION_GL_THRESHOLD:
        return "caution"
    return "unsafe"


def get_gi_category(glycemic_index: float) -> str:
    """Determine safety category based on glycemic index.
    
    Args:
        glycemic_index: Glycemic index value.
    
    Returns:
        "safe" if GI <= SAFE_GI_THRESHOLD,
        "caution" if GI > SAFE_GI_THRESHOLD and <= CAUTION_GI_THRESHOLD,
        "unsafe" if GI > CAUTION_GI_THRESHOLD.
    """
    if glycemic_index <= SAFE_GI_THRESHOLD:
        return "safe"
    if glycemic_index <= CAUTION_GI_THRESHOLD:
        return "caution"
    return "unsafe"


def evaluate_propositions(features: Dict) -> Tuple[str, str]:
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
    gl_cat = get_gl_category(gl)
    gi_cat = get_gi_category(gi)

    if gl_cat == "unsafe" or gi_cat == "unsafe":
        label = "unsafe"
    elif gl_cat == "caution" or gi_cat == "caution":
        label = "caution"
    else:
        label = "safe"

    parts = []
    if gl <= SAFE_GL_THRESHOLD:
        parts.append(f"Glycemic load {gl:.1f} within safe range (≤{SAFE_GL_THRESHOLD}).")
    elif gl <= CAUTION_GL_THRESHOLD:
        parts.append(f"Glycemic load {gl:.1f} exceeds safe threshold ({SAFE_GL_THRESHOLD}); within caution range (≤{CAUTION_GL_THRESHOLD}).")
    else:
        parts.append(f"Glycemic load {gl:.1f} exceeds caution threshold ({CAUTION_GL_THRESHOLD}).")

    if gi <= SAFE_GI_THRESHOLD:
        parts.append(f"Glycemic index {gi:.1f} within safe range (≤{SAFE_GI_THRESHOLD}).")
    elif gi <= CAUTION_GI_THRESHOLD:
        parts.append(f"Glycemic index {gi:.1f} exceeds safe threshold ({SAFE_GI_THRESHOLD}); within caution range (≤{CAUTION_GI_THRESHOLD}).")
    else:
        parts.append(f"Glycemic index {gi:.1f} exceeds caution threshold ({CAUTION_GI_THRESHOLD}).")

    explanation = " ".join(parts)
    return (label, explanation)
