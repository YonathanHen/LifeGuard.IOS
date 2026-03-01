#!/usr/bin/env python
"""
SignalFlow — Run backtest
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine


def main():
    print("Running backtest (AAPL, daily, refit every 5 days)...")
    engine = BacktestEngine(symbol="AAPL", horizon="daily", refit_every=5)
    result = engine.run(period="3y")

    print("\n--- Backtest Results ---")
    print(f"Sharpe Ratio:    {result.sharpe_ratio:.3f}")
    print(f"Max Drawdown:    {result.max_drawdown:.1%}")
    print(f"Total Return:    {result.total_return:.1%}")
    print(f"Number of Trades: {result.n_trades}")
    print(f"Hit Rate (long): {result.hit_rate:.1%}")


if __name__ == "__main__":
    main()
