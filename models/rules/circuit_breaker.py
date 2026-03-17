"""
SignalFlow — Circuit Breaker & Drawdown Throttle

- Circuit Breaker: block new positions when drawdown exceeds threshold.
- Drawdown Throttle: scale position size down when in drawdown.
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional


def _load_paper_decisions(path: Path) -> list:
    if not path.exists():
        return []
    import json
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("decisions", [])


def get_paper_equity_drawdown(
    decisions: List[Dict],
    returns_series,
    symbol: str,
) -> Tuple[float, float, float]:
    """
    Compute paper equity curve and current drawdown from decisions + returns.

    Returns: (current_equity, current_drawdown_pct, peak_equity)
    current_drawdown_pct is 0.0 to 1.0 (e.g. 0.15 = 15%).
    """
    if not decisions or returns_series is None or len(returns_series) < 2:
        return 1.0, 0.0, 1.0

    returns = returns_series.dropna()
    by_date = {
        d["date"]: d for d in decisions
        if d.get("date") and d.get("symbol", "").upper() == symbol.upper()
    }
    cum = 1.0
    peak = 1.0
    for i in range(len(returns) - 1):
        dt = returns.index[i]
        dt_str = dt.strftime("%Y-%m-%d")
        if dt_str not in by_date:
            continue
        rec = by_date[dt_str]
        if not rec.get("has_edge_final", False):
            continue
        pos_pct = rec.get("position_pct", 100) / 100.0
        next_ret = returns.iloc[i + 1]
        cum *= 1 + pos_pct * next_ret
        if cum > peak:
            peak = cum
    current_dd = (peak - cum) / peak if peak > 0 else 0.0
    return cum, current_dd, peak


def check_circuit_breaker(
    decisions: List[Dict],
    returns_series,
    symbol: str,
    threshold_pct: float = 0.15,
) -> Tuple[bool, float]:
    """
    Check if circuit breaker is tripped (drawdown > threshold).

    Returns: (tripped: bool, current_drawdown_pct: float)
    """
    _, dd, _ = get_paper_equity_drawdown(decisions, returns_series, symbol)
    tripped = dd >= threshold_pct
    return tripped, dd


def get_drawdown_throttle(
    current_dd_pct: float,
    throttle_15_pct: float = 0.5,
    throttle_10_pct: float = 0.75,
) -> float:
    """
    Return position size multiplier based on current drawdown.

    - dd >= 15%: return throttle_15_pct (default 0.5)
    - dd >= 10%: return throttle_10_pct (default 0.75)
    - else: return 1.0
    """
    if current_dd_pct >= 0.15:
        return throttle_15_pct
    if current_dd_pct >= 0.10:
        return throttle_10_pct
    return 1.0
