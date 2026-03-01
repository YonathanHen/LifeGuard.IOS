"""
SignalFlow — Preprocessing
- Validate raw vs adjusted (splits, dividends)
- Z-score / Fat-Tail filter (rolling window)
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


def validate_adjustments(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate raw Close vs Adj Close. Flag suspicious jumps.
    """
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    # Pct change — detect splits/dividend jumps
    adj_pct = df["Adj Close"].pct_change()
    raw_pct = df["Close"].pct_change()

    # Large divergence = adjustment event
    divergence = np.abs(adj_pct - raw_pct)
    df["_adjustment_flag"] = divergence > 0.05  # 5% divergence

    return df


def z_score_filter(
    returns: pd.Series,
    window: int = 30,
    threshold: float = 3.0,
) -> Tuple[pd.Series, pd.Series]:
    """
    Rolling Z-score filter. Returns (mask_valid, z_scores).
    |z| > threshold → reduce weight or mark unstable.
    """
    rolling_mean = returns.rolling(window, min_periods=window // 2).mean()
    rolling_std = returns.rolling(window, min_periods=window // 2).std()
    z_scores = (returns - rolling_mean) / (rolling_std + 1e-8)
    mask_valid = np.abs(z_scores) <= threshold
    return mask_valid, z_scores


def preprocess(
    df: pd.DataFrame,
    horizon: str = "daily",
    z_window: Optional[int] = None,
) -> pd.DataFrame:
    """
    Full preprocessing: validate adjustments, compute returns,
    apply z-score filter, drop NaN.
    """
    df = validate_adjustments(df)

    # Use Adj Close for analysis
    close = df["Adj Close"]

    # Returns
    returns = close.pct_change().dropna()

    # Z-score filter — window by horizon
    if z_window is None:
        z_window = 30 if horizon == "daily" else (20 if horizon == "weekly" else 12)

    mask_valid, z_scores = z_score_filter(returns, window=z_window)
    df_out = pd.DataFrame(index=returns.index)
    df_out["returns"] = returns
    df_out["z_score"] = z_scores
    df_out["_stable"] = mask_valid

    # Mark unstable periods (for Rule Engine)
    df_out["_unstable"] = ~mask_valid

    return df_out.dropna()
