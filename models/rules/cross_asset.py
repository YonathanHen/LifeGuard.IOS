"""
SignalFlow — Cross-Asset Confirmation
Logic: SP500↑ + VIX↑ strongly → conflict, confidence drops.
SP500↓ + VIX↑ → makes sense (risk-off).
SP500↑ + VIX↓/flat → aligned.
"""
import pandas as pd
from typing import Tuple
from data.fetchers.cross_asset import fetch_cross_asset


def check_cross_asset_alignment_from_series(
    sp: pd.Series,
    vix: pd.Series,
    lookback_days: int = 5,
    vix_rise_threshold_pct: float = 10.0,
) -> Tuple[bool, str]:
    """
    Same logic as check_cross_asset_alignment but on pre-fetched series.
    For backtest when we have historical SP/VIX slices.
    """
    if sp.empty or vix.empty or len(sp) < lookback_days or len(vix) < lookback_days:
        return True, "Cross-Asset: insufficient data, assuming ok"

    common = sp.index.intersection(vix.index)
    if len(common) < lookback_days:
        return True, "Cross-Asset: insufficient overlap"

    sp_recent = sp.loc[common].tail(lookback_days)
    vix_recent = vix.loc[common].tail(lookback_days)

    sp_change = (sp_recent.iloc[-1] / sp_recent.iloc[0]) - 1
    vix_change = (vix_recent.iloc[-1] / vix_recent.iloc[0]) - 1

    sp_up = sp_change > 0.005
    sp_down = sp_change < -0.005
    vix_up_strong = vix_change > (vix_rise_threshold_pct / 100)
    vix_up = vix_change > 0.02

    if sp_up and vix_up_strong:
        return False, "SP500↑ but VIX↑ strongly — cross-asset conflict (fear rising)"
    if sp_up and vix_up:
        return False, "SP500↑ but VIX↑ — cross-asset weakened"
    if sp_down and vix_up:
        return True, "SP500↓ and VIX↑ — risk-off aligned"
    if sp_up and not vix_up:
        return True, "SP500↑ and VIX stable/down — aligned"
    return True, "Cross-Asset aligned"


def check_cross_asset_alignment(
    horizon: str = "daily",
    lookback_days: int = 5,
    vix_rise_threshold_pct: float = 10.0,
) -> Tuple[bool, str]:
    """
    Returns (aligned: bool, reason: str).
    aligned=False when SP500↑ but VIX↑ strongly — market says risk, we say up.
    """
    sp, vix = fetch_cross_asset(horizon=horizon, period="6mo")
    return check_cross_asset_alignment_from_series(
        sp, vix, lookback_days, vix_rise_threshold_pct
    )
