"""SignalFlow — Model tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import (
    has_statistical_edge,
    confidence_factors,
    overall_confidence,
    system_assessment,
)


@pytest.fixture
def sample_returns():
    np.random.seed(42)
    return pd.Series(np.random.randn(200) * 0.01)


def test_arima_fit_predict(sample_returns):
    """ARIMA fits and returns valid bucket."""
    model = ARIMAModel(order=(1, 0, 1))
    model.fit(sample_returns)
    out = model.predict_next()
    assert out["direction"] in ("up", "down", "flat")
    assert out["magnitude"] in ("low", "medium")


def test_garch_fit_predict(sample_returns):
    """GARCH fits and returns volatility bucket."""
    model = GARCHModel()
    model.fit(sample_returns)
    out = model.predict_next()
    assert out["volatility_bucket"] in ("low", "medium", "high")
    assert "volatility_annual_pct" in out


def test_has_statistical_edge():
    """Edge logic: flat = no edge, up/down with magnitude = edge."""
    assert has_statistical_edge({"direction": "flat", "magnitude": "low"}, {"volatility_bucket": "low"}) is False
    assert has_statistical_edge({"direction": "up", "magnitude": "low"}, {"volatility_bucket": "low"}) is True


def test_confidence_logical_and():
    """One negative factor → confidence drops."""
    factors_all_pass = [("a", True), ("b", True)]
    factors_one_fail = [("a", True), ("b", False)]
    assert overall_confidence(factors_all_pass) == "high"
    assert overall_confidence(factors_one_fail) == "medium"


def test_system_assessment():
    """Assessment reflects has_edge and risk."""
    no_edge = system_assessment(False, "low", "high")
    assert "avoid" in no_edge.lower()
    with_edge = system_assessment(True, "high", "low")
    assert "edge" in with_edge.lower()
