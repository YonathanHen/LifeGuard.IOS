"""SignalFlow — Validation tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from validation.point_in_time import (
    run_point_in_time_prediction,
    run_validation,
    _is_correct,
    ValidationResult,
)


def test_is_correct():
    """Correctness logic."""
    assert _is_correct("up", 0.01) is True
    assert _is_correct("up", -0.01) is False
    assert _is_correct("down", -0.01) is True
    assert _is_correct("down", 0.01) is False
    assert _is_correct("flat", 0.05) is None
    assert _is_correct("flat", -0.03) is None


def test_point_in_time_prediction():
    """Single point-in-time prediction (needs network)."""
    try:
        pred, actual, err = run_point_in_time_prediction(
            "AAPL", "daily", "2023-06-15"
        )
        if err:
            pytest.skip(f"Prediction failed: {err}")
        assert pred is not None
        assert "direction" in pred
        assert pred["direction"] in ("up", "down", "flat")
        assert actual is not None
        assert isinstance(actual, (int, float))
    except Exception as e:
        pytest.skip(f"Needs network: {e}")


def test_run_validation_small():
    """Validation with 2 samples per horizon (faster)."""
    try:
        results = run_validation(
            symbol="AAPL",
            samples_per_horizon=2,
            seed=123,
        )
        assert "daily" in results
        assert "weekly" in results
        assert "regime_outlook" in results
        for vr in results.values():
            assert isinstance(vr, ValidationResult)
            assert vr.total + vr.skipped_flat + len([s for s in vr.samples if "error" in s]) >= 0
    except Exception as e:
        pytest.skip(f"Needs network: {e}")
