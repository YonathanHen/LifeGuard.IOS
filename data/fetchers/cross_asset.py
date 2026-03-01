"""
SignalFlow — Cross-Asset Fetcher (SP500, VIX)
For Cross-Asset Confirmation. Must match time horizon.
Uses same SSL setup as yahoo_finance (certifi).
Load yahoo_finance first so env vars are set.
"""
import pandas as pd
import yfinance as yf
from typing import Tuple, Optional
from datetime import datetime


def fetch_cross_asset(
    horizon: str = "daily",
    period: str = "1y",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[pd.Series, pd.Series]:
    """
    Fetch SP500 and VIX. Returns (sp500_series, vix_series).
    Aligns both to common dates (forward-fill for gaps).
    For backtest: pass start_date, end_date instead of period.
    """
    interval = "1d" if horizon in ("daily", "weekly") else "1wk"
    if start_date is not None and end_date is not None:
        sp = yf.Ticker("^GSPC").history(start=start_date, end=end_date, interval=interval)
        vix = yf.Ticker("^VIX").history(start=start_date, end=end_date, interval=interval)
    else:
        sp = yf.Ticker("^GSPC").history(period=period, interval=interval)
        vix = yf.Ticker("^VIX").history(period=period, interval=interval)

    if sp.empty or vix.empty:
        return pd.Series(), pd.Series()

    sp_close = sp["Adj Close"] if "Adj Close" in sp.columns else sp["Close"]
    vix_close = vix["Adj Close"] if "Adj Close" in vix.columns else vix["Close"]

    if horizon == "weekly":
        sp_close = sp_close.resample("W").last().dropna()
        vix_close = vix_close.resample("W").last().dropna()

    # Align to common index — union, forward-fill, then inner join
    common_idx = sp_close.index.union(vix_close.index).drop_duplicates().sort_values()
    sp_aligned = sp_close.reindex(common_idx).ffill().dropna()
    vix_aligned = vix_close.reindex(common_idx).ffill().dropna()
    # Inner join for valid pairs only
    valid_idx = sp_aligned.index.intersection(vix_aligned.index)
    return sp_aligned.loc[valid_idx], vix_aligned.loc[valid_idx]
