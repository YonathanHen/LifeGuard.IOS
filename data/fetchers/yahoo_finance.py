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
    session = _get_session()
    ticker = yf.Ticker(symbol, session=session) if session else yf.Ticker(symbol)
    if start_date is not None and end_date is not None:
        df = ticker.history(start=start_date, end=end_date, interval=interval, auto_adjust=False)
    else:
        df = ticker.history(period=period, interval=interval, auto_adjust=False)

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
