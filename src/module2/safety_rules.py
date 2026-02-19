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
    elif glycemic_load <= CAUTION_GL_THRESHOLD:
        return "caution"
    else:
        return "unsafe"
    pass


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
    elif glycemic_index <= CAUTION_GI_THRESHOLD:
        return "caution"
    else:
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
    # TODO: Implement
    # 1. Extract GI and GL from features dict
    gi = features["glycemic_index"]
    gl = features["glycemic_load"]
    # 2. Call get_gl_category(gl) and get_gi_category(gi) to get categories
    gl_category = get_gl_category(gl)
    gi_category = get_gi_category(gi)
    # 3. Determine final label based on priority (unsafe > caution > safe)
    #    - If either GL or GI is "unsafe" → "unsafe"
    #    - Else if either is "caution" → "caution"
    #    - Else → "safe"
    if gl_category == "unsafe" or gi_category == "unsafe":
        return "unsafe"
    elif gl_category == "caution" or gi_category == "caution":
        return "caution"
    else:
        return "safe"
    # 4. Build explanation string mentioning which rules fired and their values/thresholds
    #    Example: "Glycemic load 18.5 exceeds safe threshold (10); within caution range (≤20). Glycemic index within safe range (52)."
    explanation = f"Glycemic load {gl} exceeds safe threshold ({SAFE_GL_THRESHOLD}); within caution range ({CAUTION_GL_THRESHOLD}). Glycemic index {gi} within safe range ({SAFE_GI_THRESHOLD})."
    return (label, explanation)
