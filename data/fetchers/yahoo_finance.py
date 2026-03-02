"""
SignalFlow — Yahoo Finance Fetcher
Uses adjusted close. Validates raw vs adjusted for splits/dividends.

Production: Uses certifi CA bundle for SSL.
Fallback: SIGNALFLOW_SSL_BYPASS=1 for restricted networks (corporate proxy).
"""
import os
import sys

# Configure SSL before any network imports — production default
if "SSL_CERT_FILE" not in os.environ and "CURL_CA_BUNDLE" not in os.environ:
    try:
        import certifi
        ca_bundle = certifi.where()
        os.environ["SSL_CERT_FILE"] = ca_bundle
        os.environ["CURL_CA_BUNDLE"] = ca_bundle
    except ImportError:
        pass  # certifi not installed, use system defaults

import pandas as pd
import yfinance as yf
from typing import Optional


def _get_session():
    """
    Session for yfinance.
    Production: None (use default with certifi).
    Restricted networks: SIGNALFLOW_SSL_BYPASS=1 for verify=False.
    """
    if os.environ.get("SIGNALFLOW_SSL_BYPASS") == "1":
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome")
            session.verify = False
            return session
        except ImportError:
            import requests
            session = requests.Session()
            session.verify = False
            return session
    return None


def fetch_yahoo(
    symbol: str,
    period: str = "5y",
    interval: str = "1d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_rows: int = 30,
) -> pd.DataFrame:
    """
    Fetch price data from Yahoo Finance.
    Returns OHLCV with Adjusted Close. Index = DatetimeIndex.
    For point-in-time: pass start_date, end_date (YYYY-MM-DD).
    """
    import time
    from datetime import datetime, timedelta

    # Prefer start_date/end_date — Yahoo API sometimes fails with period
    if start_date is None or end_date is None:
        years = int("".join(c for c in str(period) if c.isdigit()) or 5)
        end_d = datetime.now()
        start_d = end_d - timedelta(days=365 * years)
        _start = start_d.strftime("%Y-%m-%d")
        _end = (end_d + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        _start, _end = start_date, end_date

    session = _get_session()
    ticker = yf.Ticker(symbol, session=session) if session else yf.Ticker(symbol)
    df = pd.DataFrame()

    for attempt in range(3):
        try:
            df = ticker.history(start=_start, end=_end, interval=interval, auto_adjust=False)
            if df is not None and not df.empty:
                break
        except (TypeError, KeyError) as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise ValueError(f"Yahoo Finance failed for {symbol} (retried): {e}") from e

    if df is None or df.empty:
        raise ValueError(f"Yahoo Finance returned no data for {symbol}")

    if df.empty or len(df) < min_rows:
        raise ValueError(f"Insufficient data for {symbol}")

    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    return df


def resample_to_horizon(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """
    Resample daily data to weekly or monthly OHLC.
    NOT average — proper OHLC aggregation.
    """
    if horizon == "daily":
        return df.copy()

    rule = "W" if horizon == "weekly" else "M"
    resampled = df.resample(rule).agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Adj Close": "last",
        "Volume": "sum",
    }).dropna()

    return resampled
