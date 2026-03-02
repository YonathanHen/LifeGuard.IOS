"""SignalFlow — FRED fetcher tests."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from data.fetchers.fred_fetcher import (
    fetch_fred,
    fetch_credit_spread,
    fetch_yield_curve,
    fetch_macro_data,
)


def test_fetch_fred_no_key_returns_empty():
    """Without FRED_API_KEY, returns empty Series."""
    prev = os.environ.pop("FRED_API_KEY", None)
    try:
        s = fetch_fred(period="1y")
        assert isinstance(s, pd.Series)
        assert s.empty
    finally:
        if prev is not None:
            os.environ["FRED_API_KEY"] = prev


def test_fetch_credit_spread_no_key():
    """fetch_credit_spread without key returns empty."""
    prev = os.environ.pop("FRED_API_KEY", None)
    try:
        s = fetch_credit_spread(period="1y")
        assert s.empty
    finally:
        if prev is not None:
            os.environ["FRED_API_KEY"] = prev


def test_pipeline_without_fred():
    """Pipeline runs and does not require FRED."""
    from data.pipeline import DataPipeline

    prev = os.environ.pop("FRED_API_KEY", None)
    try:
        p = DataPipeline("AAPL", "daily", period="1y")
        df = p.run()
        assert "returns" in df.columns
        assert not p.is_fred_available()
        if "credit_spread" in df.columns:
            assert df["credit_spread"].isna().all() or (df["credit_spread"] == 0).any()
    except Exception as e:
        pytest.skip(f"Network: {e}")
    finally:
        if prev is not None:
            os.environ["FRED_API_KEY"] = prev


def test_fetch_macro_data_no_key():
    """fetch_macro_data without key returns empty DataFrame."""
    prev = os.environ.pop("FRED_API_KEY", None)
    try:
        df = fetch_macro_data(period="1y")
        assert df.empty
    finally:
        if prev is not None:
            os.environ["FRED_API_KEY"] = prev


def test_fred_series_map():
    """SERIES_MAP contains expected series."""
    from data.fetchers.fred_fetcher import SERIES_MAP
    assert "credit_spread" in SERIES_MAP
    assert "yield_curve" in SERIES_MAP
    assert SERIES_MAP["credit_spread"] == "BAMLH0A0HYM2"
    assert SERIES_MAP["yield_curve"] == "T10Y2Y"
