"""
SignalFlow — Short-Term Reversal (Oversold Screening)

In mean_reverting regime: only enter when stock is oversold (1m return < 0).
Exploits bounce-after-dip in mean-reversion.
"""
import numpy as np
import pandas as pd
from typing import Tuple


def is_oversold_1m(returns: pd.Series, as_of_index: int, min_bars: int = 21) -> Tuple[bool, float]:
    """
    Check if 1-month (21 trading days) return is negative (oversold).

    Returns: (oversold: bool, return_1m: float)
    """
    if returns is None or len(returns) < min_bars or as_of_index < min_bars:
        return True, 0.0  # default allow if not enough data
    start = as_of_index - min_bars
    subset = returns.iloc[start:as_of_index + 1]
    cum = (1 + subset).prod() - 1.0
    return cum < 0, float(cum)
