"""
SignalFlow — FRED Fetcher (Credit Spreads, Yield Curve, Macro)
External Feature Layer — Phase 2A.
Uses FRED API (free key: https://fred.stlouisfed.org/docs/api/api_key.html)

Series:
- BAMLH0A0HYM2: High Yield OAS — credit spread (פחד בשוק)
- T10Y2Y: 10Y-2Y yield spread — recession/growth indicator
"""
import os
import logging
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta

SERIES_MAP = {
    "credit_spread": "BAMLH0A0HYM2",
    "yield_curve": "T10Y2Y",
}

log = logging.getLogger(__name__)


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
        series_id=SERIES_MAP["credit_spread"],
        start_date=start_date,
        end_date=end_date,
        period=period,
    )


def fetch_yield_curve(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "5y",
) -> pd.Series:
    """
    Fetch 10Y-2Y Yield Spread (T10Y2Y).
    Negative = inverted curve (recession signal). Positive = normal.
    """
    return fetch_fred(
        series_id=SERIES_MAP["yield_curve"],
        start_date=start_date,
        end_date=end_date,
        period=period,
    )


def fetch_macro_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "5y",
    series: Optional[list] = None,
) -> pd.DataFrame:
    """
    Fetch multiple FRED series. Returns DataFrame with columns per series.
    Uses ffill for gaps (macro data often lower frequency).
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        return pd.DataFrame()

    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
    except ImportError:
        return pd.DataFrame()

    if start_date is None or end_date is None:
        end = datetime.now()
        if "y" in period:
            years = int("".join(c for c in period if c.isdigit()) or 5)
            start = end - timedelta(days=365 * years)
        else:
            start = end - timedelta(days=365 * 2)
        start_date = start.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")

    to_fetch = series or list(SERIES_MAP.keys())
    dfs = []
    for name in to_fetch:
        sid = SERIES_MAP.get(name)
        if not sid:
            continue
        try:
            s = fred.get_series(sid, observation_start=start_date, observation_end=end_date)
            if s is not None and not s.empty:
                s = s.dropna()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                df = pd.DataFrame({name: s})
                dfs.append(df)
        except Exception as e:
            log.warning("FRED fetch %s: %s", name, e)

    if not dfs:
        return pd.DataFrame()
    out = pd.concat(dfs, axis=1).sort_index().ffill()
    return out
