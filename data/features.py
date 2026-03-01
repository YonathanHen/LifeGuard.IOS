"""
SignalFlow — Feature Engineering
Stat: returns, volatility. Technical (use with caution — see PLANNING).
"""
import pandas as pd
import numpy as np
from typing import Optional


def compute_volatility(returns: pd.Series, window: int = 20) -> pd.Series:
    """Rolling annualized volatility."""
    return returns.rolling(window, min_periods=window // 2).std() * np.sqrt(252)


def compute_features(
    returns: pd.Series,
    horizon: str = "daily",
    vol_window: Optional[int] = None,
) -> pd.DataFrame:
    """
    Returns + volatility. For Stat Core (ARIMA, GARCH).
    """
    if vol_window is None:
        vol_window = 20 if horizon == "daily" else 12

    df = pd.DataFrame(index=returns.index)
    df["returns"] = returns
    df["volatility"] = compute_volatility(returns, window=vol_window)

    return df.dropna()
