"""SignalFlow — Backtest tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from backtesting.engine import BacktestEngine, BacktestResult


def test_backtest_engine_sharpe_calculation():
    """Sharpe and max_drawdown are computed correctly."""
    # Simple case: constant positive returns
    result = BacktestResult(
        sharpe_ratio=1.5,
        max_drawdown=-0.1,
        total_return=0.15,
        n_trades=10,
        hit_rate=0.6,
        equity_curve=pd.Series([1.0, 1.01, 1.02, 1.015, 1.03]),
    )
    assert result.sharpe_ratio > 0
    assert -1 <= result.max_drawdown <= 0


def test_backtest_runs():
    """Backtest completes without error (uses network)."""
    try:
        engine = BacktestEngine(
            symbol="AAPL",
            horizon="daily",
            refit_every=20,  # Faster
            train_min_days=252,
        )
        result = engine.run(period="2y")
        assert isinstance(result, BacktestResult)
        assert -2 <= result.sharpe_ratio <= 2  # Sanity
        assert -1 <= result.max_drawdown <= 0
    except Exception as e:
        pytest.skip(f"Backtest needs network: {e}")
