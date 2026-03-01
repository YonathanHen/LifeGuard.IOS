"""
SignalFlow — FRED Fetcher (Credit Spreads, Macro)
External Feature Layer — Phase 2A.
Uses FRED API (free key: https://fred.stlouisfed.org/docs/api/api_key.html)
"""
import os
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta


def fetch_fred(
    series_id: str = "BAMLH0A0HYM2",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "5y",
) -> pd.Series:
    """
    Fetch FRED series. Default: BAMLH0A0HYM2 (High Yield OAS — credit spread).
    Returns Series with DatetimeIndex. Empty if no API key or fetch fails.
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        return pd.Series(dtype=float)

    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
    except ImportError:
        return pd.Series(dtype=float)

    if start_date is None or end_date is None:
        end = datetime.now()
        if "y" in period:
            years = int("".join(c for c in period if c.isdigit()) or 5)
            start = end - timedelta(days=365 * years)
        else:
            start = end - timedelta(days=365 * 2)
        start_date = start.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")

    try:
        s = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        if s is None or s.empty:
            return pd.Series(dtype=float)
        s = s.dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        return pd.Series(s)
    except Exception:
        return pd.Series(dtype=float)


def fetch_credit_spread(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "5y",
) -> pd.Series:
    """
    Fetch High Yield Credit Spread (BAMLH0A0HYM2).
    Daily, no publication lag — available same day.
    """
    return fetch_fred(
        series_id="BAMLH0A0HYM2",
        start_date=start_date,
        end_date=end_date,
        period=period,
    )
