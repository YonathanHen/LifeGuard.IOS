"""
SignalFlow — FRED Fetcher (Credit Spreads, Yield Curve, Macro)
External Feature Layer — Phase 2A.
Uses FRED API (free key: https://fred.stlouisfed.org/docs/api/api_key.html)

Series:
- BAMLH0A0HYM2: High Yield OAS — credit spread (פחד בשוק)
- T10Y2Y: 10Y-2Y yield spread — recession/growth indicator

Cache: Local storage/fred_cache/ to avoid rate limits. TTL=24h for live data.
"""
import os
import logging
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

SERIES_MAP = {
    "credit_spread": "BAMLH0A0HYM2",
    "yield_curve": "T10Y2Y",
}

CACHE_TTL_HOURS = 24
CACHE_DIR = Path(__file__).resolve().parents[2] / "storage" / "fred_cache"

log = logging.getLogger(__name__)


def _cache_path(series_id: str) -> Path:
    """Cache file path for a series."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{series_id}.parquet"


def _cache_path_csv(series_id: str) -> Path:
    """Fallback: CSV path (no pyarrow required)."""
    return CACHE_DIR / f"{series_id}.csv"


def _load_cache(series_id: str) -> Optional[pd.Series]:
    """Load cached series if exists and valid."""
    for ext, reader in [(".parquet", lambda p: pd.read_parquet(p)), (".csv", lambda p: pd.read_csv(p, index_col=0, parse_dates=True))]:
        p = CACHE_DIR / f"{series_id}{ext}"
        if not p.exists():
            continue
        try:
            df = reader(p)
            if df.empty or "value" not in df.columns:
                return None
            s = df["value"].copy()
            s.index = pd.to_datetime(s.index)
            return s
        except Exception as e:
            log.debug("FRED cache read %s: %s", series_id, e)
    return None


def _save_cache(series_id: str, s: pd.Series) -> None:
    """Save series to cache. Prefer parquet; fallback to CSV."""
    if s is None or s.empty:
        return
    df = pd.DataFrame({"value": s})
    try:
        df.to_parquet(_cache_path(series_id))
    except Exception:
        try:
            df.to_csv(_cache_path_csv(series_id))
        except Exception as e:
            log.debug("FRED cache write %s: %s", series_id, e)


def _cache_is_fresh(series_id: str) -> bool:
    """True if cache was updated within TTL (for live data)."""
    for p in [_cache_path(series_id), _cache_path_csv(series_id)]:
        if p.exists():
            age_hours = (datetime.now().timestamp() - p.stat().st_mtime) / 3600
            return age_hours < CACHE_TTL_HOURS
    return False


def _fetch_fred_api(
    fred,
    series_id: str,
    start_date: str,
    end_date: str,
) -> pd.Series:
    """Call FRED API. Returns empty Series on failure."""
    try:
        s = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        if s is None or s.empty:
            return pd.Series(dtype=float)
        s = s.dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        return pd.Series(s)
    except Exception as e:
        log.warning("FRED fetch %s: %s", series_id, e)
        return pd.Series(dtype=float)


def fetch_fred(
    series_id: str = "BAMLH0A0HYM2",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "5y",
) -> pd.Series:
    """
    Fetch FRED series. Uses local cache to avoid rate limits.
    Returns Series with DatetimeIndex. Empty if no API key or fetch fails.
    """
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        # Try cache as fallback even without API key (e.g. rate limit recovery)
        cached = _load_cache(series_id)
        if cached is not None:
            start_d = pd.Timestamp(start_date) if start_date else pd.Timestamp.now() - pd.Timedelta(days=365 * 5)
            end_d = pd.Timestamp(end_date) if end_date else pd.Timestamp.now()
            mask = (cached.index >= start_d) & (cached.index <= end_d)
            return cached.loc[mask].copy()
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

    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    is_historical = end_ts.date() < datetime.now().date()

    # 1. Check cache
    cached = _load_cache(series_id)
    if cached is not None and not cached.empty:
        cache_start = cached.index.min()
        cache_end = cached.index.max()
        covers = cache_start <= start_ts and cache_end >= end_ts
        if covers:
            if is_historical:
                # Historical data never changes — use cache
                mask = (cached.index >= start_ts) & (cached.index <= end_ts)
                return cached.loc[mask].copy()
            if _cache_is_fresh(series_id):
                mask = (cached.index >= start_ts) & (cached.index <= end_ts)
                return cached.loc[mask].copy()

    # 2. Fetch from API
    s = _fetch_fred_api(fred, series_id, start_date, end_date)
    if s is not None and not s.empty:
        # Merge with cache if we have partial cache (extend coverage)
        if cached is not None and not cached.empty:
            combined = pd.concat([cached, s])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            _save_cache(series_id, combined)
        else:
            _save_cache(series_id, s)
        mask = (s.index >= start_ts) & (s.index <= end_ts)
        return s.loc[mask].copy()

    # 3. API failed — fallback to stale cache if covers range
    if cached is not None and not cached.empty:
        cache_start = cached.index.min()
        cache_end = cached.index.max()
        if cache_start <= start_ts and cache_end >= end_ts:
            log.info("FRED %s: using cached fallback (API failed)", series_id)
            mask = (cached.index >= start_ts) & (cached.index <= end_ts)
            return cached.loc[mask].copy()

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
    Uses fetch_fred internally → benefits from local cache.
    """
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
        s = fetch_fred(
            series_id=sid,
            start_date=start_date,
            end_date=end_date,
            period=period,
        )
        if s is not None and not s.empty:
            df = pd.DataFrame({name: s})
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()
    out = pd.concat(dfs, axis=1).sort_index().ffill()
    return out
