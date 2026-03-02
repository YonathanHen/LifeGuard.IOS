"""
SignalFlow — Ensemble Logic (Phase 2B)
Decision = Stat Core Edge AND LSTM P(up/down) > threshold
"""
from typing import Dict, Any, Optional, Tuple


def ml_supports_direction(
    ml_probs: Optional[Dict[str, float]],
    direction: str,
    threshold: float = 0.6,
) -> Tuple[bool, Optional[str]]:
    """
    Check if ML layer supports the Stat Core direction.
    direction: "up" | "down"
    Returns (supported, reason).
    """
    if ml_probs is None:
        return True, "ML not available — Stat Core only (fallback)"
    p_up = ml_probs.get("P_up", 0.0)
    p_down = ml_probs.get("P_down", 0.0)
    p_flat = ml_probs.get("P_flat", 0.0)

    if direction == "up":
        if p_up >= threshold:
            return True, f"ML P(up)={p_up:.2f} >= {threshold}"
        return False, f"ML P(up)={p_up:.2f} < {threshold}"
    if direction == "down":
        if p_down >= threshold:
            return True, f"ML P(down)={p_down:.2f} >= {threshold}"
        return False, f"ML P(down)={p_down:.2f} < {threshold}"
    # flat
    return False, "Stat Core direction is flat"


def ensemble_decision(
    has_edge: bool,
    direction: str,
    ml_probs: Optional[Dict[str, float]],
    threshold: float = 0.6,
) -> Tuple[bool, str]:
    """
    Final decision: Trade only if Stat Core Edge AND ML supports direction.
    Returns (should_trade, reason).
    """
    if not has_edge:
        return False, "No statistical edge"
    if direction == "flat":
        return False, "Direction flat"
    supported, ml_reason = ml_supports_direction(ml_probs, direction, threshold)
    if supported:
        return True, ml_reason
    return False, ml_reason


def ensemble_decision_negative_filter(
    has_edge: bool,
    direction: str,
    ml_probs: Optional[Dict[str, float]],
    disaster_threshold: float = 0.80,
) -> Tuple[bool, str]:
    """
    Negative Filter: Trade if Stat Core says Long, UNLESS ML is very confident of drop.
    Block only when P_down > disaster_threshold (e.g. 0.80).
    Use when ML has pessimistic bias - avoid blocking good trades, only block disasters.
    Returns (should_trade, reason).
    """
    if not has_edge:
        return False, "No statistical edge"
    if direction != "up":
        return False, "Stat direction not Long"
    if ml_probs is None:
        return True, "ML not available - allow (Stat only fallback)"
    p_down = ml_probs.get("P_down", 0.0)
    if p_down > disaster_threshold:
        return False, f"ML P(down)={p_down:.2f} > {disaster_threshold} (block disaster)"
    return True, f"ML P(down)={p_down:.2f} <= {disaster_threshold} (allow)"
