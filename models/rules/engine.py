"""
SignalFlow — Rule Engine
- Has edge? (ARIMA + GARCH aligned, magnitude above threshold)
- Liquidity gate
- Confidence = Logical AND (one negative → falls)
"""
from typing import Dict, Any, List, Tuple


def has_statistical_edge(
    arima_out: Dict[str, Any],
    garch_out: Dict[str, Any],
    min_magnitude: str = "low",
) -> bool:
    """
    Edge = bucket clear (not flat) + magnitude above threshold.
    """
    direction = arima_out.get("direction", "flat")
    magnitude = arima_out.get("magnitude", "low")

    if direction == "flat":
        return False

    mag_order = {"low": 1, "medium": 2}
    min_order = mag_order.get(min_magnitude, 1)
    mag_val = mag_order.get(magnitude, 0)

    return mag_val >= min_order


def liquidity_gate(
    dollar_volume_20d_avg: float,
    min_volume: float = 2_000_000,
) -> bool:
    """Tradable = volume above threshold."""
    return dollar_volume_20d_avg >= min_volume


def confidence_factors(
    arima_out: Dict,
    garch_out: Dict,
    cross_asset_ok: bool,
    liquidity_ok: bool,
    regime_stable: bool,
    data_stable: bool,
    cooldown_ok: bool = True,
) -> List[Tuple[str, bool]]:
    """
    Logical AND — one negative → overall low.
    Returns list of (factor_name, passed).
    cooldown_ok: False when in Forced Cooldown after regime shift.
    """
    factors = [
        ("ARIMA direction clear", arima_out.get("direction", "flat") != "flat"),
        ("GARCH volatility reasonable", garch_out.get("volatility_bucket") != "high" or regime_stable),
        ("Cross-Asset aligned", cross_asset_ok),
        ("Liquidity sufficient", liquidity_ok),
        ("Regime stable", regime_stable),
        ("Data stable (no z-score outlier)", data_stable),
        ("Not in cooldown", cooldown_ok),
    ]
    return factors


def overall_confidence(factors: List[Tuple[str, bool]]) -> str:
    """Overall: high if all pass, medium if one fails, low otherwise."""
    passed = sum(1 for _, p in factors if p)
    total = len(factors)
    if passed == total:
        return "high"
    if passed >= total - 1:
        return "medium"
    return "low"


def system_assessment(
    has_edge: bool,
    confidence: str,
    risk_bucket: str,
) -> str:
    """Human-readable system assessment."""
    if not has_edge:
        return "No statistical edge — avoid."
    if risk_bucket == "high" and confidence != "high":
        return "Direction exists, but risk is elevated. Consider caution or reduced exposure."
    if confidence == "low":
        return "Edge present but confidence low — consider reduced exposure."
    return "Statistical edge present. Risk control remains essential."
