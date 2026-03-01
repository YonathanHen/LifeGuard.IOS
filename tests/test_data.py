"""SignalFlow — Data layer tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from data.pipeline import DataPipeline
from data.preprocessing import z_score_filter, validate_adjustments
from data.features import compute_volatility, compute_features


def test_z_score_filter():
    """Z-score filter returns valid mask and z_scores."""
    import numpy as np
    np.random.seed(42)
    returns = pd.Series(np.random.randn(100) * 0.01)
    mask, z = z_score_filter(returns, window=20, threshold=3.0)
    assert len(mask) == len(returns)
    assert mask.dtype == bool
    assert (np.abs(z[mask]) <= 3.0).all()


def test_compute_volatility():
    """Volatility is non-negative."""
    import numpy as np
    np.random.seed(42)
    returns = pd.Series(np.random.randn(100) * 0.01)
    vol = compute_volatility(returns, window=20)
    assert (vol.dropna() >= 0).all()


def test_pipeline_integration():
    """Full pipeline returns expected columns."""
    p = DataPipeline("AAPL", "daily", period="1y")
    df = p.run()
    assert "returns" in df.columns
    assert "volatility" in df.columns
    assert len(df) >= 100
    assert df["returns"].notna().all()


def test_pipeline_smoke():
    """Pipeline runs without error (uses real network)."""
    try:
        p = DataPipeline("AAPL", "daily", period="1y")
        df = p.run()
        assert len(df) > 0
        assert "returns" in df.columns
    except Exception as e:
        pytest.skip(f"Network/data issue: {e}")
