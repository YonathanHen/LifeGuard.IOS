"""
SignalFlow — Dual Momentum (Absolute Momentum)

Absolute momentum: if SPY 12m return < risk_free, go to cash.
Uses SPY as market proxy. Risk-free approximated (e.g. 4% annual).
"""
from typing import Tuple
from pathlib import Path
import sys

if str(Path(__file__).parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from data.fetchers import fetch_yahoo
except ImportError:
    fetch_yahoo = None


def check_absolute_momentum(
    end_date: str,
    lookback_months: int = 12,
    risk_free_annual: float = 0.04,
    market_symbol: str = "SPY",
) -> Tuple[bool, float]:
    """
    Check absolute momentum: SPY 12m return vs risk-free.

    Returns: (go_to_cash: bool, spy_12m_return: float)
    go_to_cash=True when SPY 12m < risk_free (bear regime).
    """
    if fetch_yahoo is None:
        return False, 0.0

    try:
        import pandas as pd
        end_d = pd.Timestamp(end_date)
        start_d = end_d - pd.Timedelta(days=lookback_months * 22)
        raw = fetch_yahoo(
            market_symbol,
            start_date=start_d.strftime("%Y-%m-%d"),
            end_date=(end_d + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if raw is None or raw.empty or len(raw) < 20:
            return False, 0.0
        close = raw["Adj Close"] if "Adj Close" in raw.columns else raw["Close"]
        close = close.dropna()
        if len(close) < 2:
            return False, 0.0
        ret_12m = (close.iloc[-1] / close.iloc[0]) - 1.0
        rf_period = risk_free_annual * (lookback_months / 12.0)
        go_to_cash = ret_12m < rf_period
        return go_to_cash, ret_12m
    except Exception:
        return False, 0.0
