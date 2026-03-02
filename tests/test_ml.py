"""SignalFlow — ML Layer tests."""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.ml.lstm_model import (
    LSTMPredictor,
    _label_from_forward_return,
    _get_ml_features,
    build_sequences,
)


def test_label_from_forward_return():
    # 10 bps = 0.001; strictly > for up, < for down
    assert _label_from_forward_return(0.0015) == 2   # up
    assert _label_from_forward_return(-0.002) == 0   # down
    assert _label_from_forward_return(0.00005) == 1  # flat
    assert _label_from_forward_return(0.001) == 1    # at boundary = flat


def test_get_ml_features():
    idx = pd.date_range("2024-01-01", periods=50, freq="B")
    df = pd.DataFrame({"returns": np.random.randn(50) * 0.01, "_stable": True}, index=idx)
    df["vix"] = 18 + np.random.rand(50) * 5
    df["credit_spread"] = 4 + np.random.rand(50)
    df["yield_curve"] = 0.3 + np.random.rand(50) * 0.2
    out = _get_ml_features(df)
    assert "returns" in out.columns
    assert "vix" in out.columns
    assert "credit_spread" in out.columns
    assert "yield_curve" in out.columns
    assert len(out) == 50


def test_get_ml_features_without_external():
    idx = pd.date_range("2024-01-01", periods=50, freq="B")
    df = pd.DataFrame({"returns": np.random.randn(50) * 0.01, "_stable": True}, index=idx)
    out = _get_ml_features(df)
    assert "vix" in out.columns
    assert "credit_spread" in out.columns
    assert "yield_curve" in out.columns
    assert (out["vix"] == 20.0).all()
    assert (out["credit_spread"] == 4.0).all()
    assert (out["yield_curve"] == 0.5).all()


def test_build_sequences():
    feat = np.random.randn(100, 3).astype(np.float32)
    labels = np.random.randint(0, 3, size=100)
    X, y = build_sequences(feat, labels, lookback=20)
    assert X.shape == (79, 20, 3)
    assert y.shape == (79,)


def test_ensemble():
    from models.ml.ensemble import ensemble_decision, ml_supports_direction
    supported, _ = ml_supports_direction({"P_up": 0.7, "P_down": 0.2, "P_flat": 0.1}, "up", 0.6)
    assert supported
    supported, _ = ml_supports_direction({"P_up": 0.5, "P_down": 0.3, "P_flat": 0.2}, "up", 0.6)
    assert not supported
    trade, _ = ensemble_decision(True, "up", {"P_up": 0.7, "P_down": 0.2, "P_flat": 0.1}, 0.6)
    assert trade
    trade, _ = ensemble_decision(False, "up", {"P_up": 0.7}, 0.6)
    assert not trade
    trade, _ = ensemble_decision(True, "up", None, 0.6)
    assert trade  # fallback when ML not available
