#!/usr/bin/env python
"""
Gemini Analysis — Answers the key questions from Gemini's review:
1. Max Drawdown: Strategy vs Buy & Hold
2. Average Trade (profit per trade %) — slippage concern if < 0.5%
3. 2022 specifically (bear year)
4. SPY vs AAPL (less volatile asset)
"""
import sys
import warnings
from pathlib import Path
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

sys.path.insert(0, str(Path(__file__).parent.parent))

import yfinance as yf
import pandas as pd
from backtesting.engine import BacktestEngine


def buy_hold_stats(symbol: str, start: str, end: str) -> dict:
    """Buy & hold return and max drawdown for given range."""
    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty or len(df) < 5:
        return {"return": 0, "max_dd": 0}
    close = df["Close"].squeeze() if hasattr(df["Close"], "squeeze") else df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    rets = close.pct_change().dropna()
    cum = (1 + rets).cumprod()
    dd = (cum / cum.cummax() - 1).min()
    total_ret = (close.iloc[-1] / close.iloc[0]) - 1
    return {"return": total_ret, "max_dd": dd}


def run_strategy(
    symbol: str,
    period: str,
    end_date: str | None = None,
    commission_bps: float = 5,
    slippage_bps: float = 3,
) -> dict:
    """Run strategy and return key metrics."""
    engine = BacktestEngine(
        symbol=symbol,
        horizon="daily",
        refit_every=5,
        use_ml=False,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
    )
    r = engine.run(period=period, end_date=end_date)
    avg_trade_pct = (r.total_return / r.n_trades * 100) if r.n_trades else 0
    return {
        "return": r.total_return,
        "sharpe": r.sharpe_ratio,
        "max_dd": r.max_drawdown,
        "n_trades": r.n_trades,
        "avg_trade_pct": avg_trade_pct,
        "hit_rate": r.hit_rate,
    }


def main():
    print("=" * 60)
    print("GEMINI ANALYSIS — Strategy vs Benchmark")
    print("=" * 60)

    # 1. 3y AAPL — Strategy vs B&H
    print("\n--- 1. 3Y AAPL (Stat Only, 5+3 bps) ---")
    r3 = run_strategy("AAPL", "3y")
    end_3y = datetime.now()
    start_3y = end_3y - timedelta(days=365 * 3)
    bnh3 = buy_hold_stats("AAPL", start_3y.strftime("%Y-%m-%d"), end_3y.strftime("%Y-%m-%d"))
    print(f"Strategy:  Return={r3['return']:.1%}  MaxDD={r3['max_dd']:.1%}  Sharpe={r3['sharpe']:.2f}")
    print(f"           Trades={r3['n_trades']}  Avg/trade={r3['avg_trade_pct']:.3f}%  HitRate={r3['hit_rate']:.1%}")
    print(f"B&H AAPL:  Return={bnh3['return']:.1%}  MaxDD={bnh3['max_dd']:.1%}")
    print(f"→ Alpha: {r3['return'] - bnh3['return']:.1%}  DD advantage: {bnh3['max_dd'] - r3['max_dd']:.1%} lower")

    # 2. 2022 — Bear year
    print("\n--- 2. 2022 (Bear Year) ---")
    r22 = run_strategy("AAPL", "2y", end_date="2022-12-31")
    bnh22 = buy_hold_stats("AAPL", "2022-01-01", "2022-12-31")
    print(f"Strategy:  Return={r22['return']:.1%}  MaxDD={r22['max_dd']:.1%}  Trades={r22['n_trades']}")
    print(f"B&H AAPL:  Return={bnh22['return']:.1%}  MaxDD={bnh22['max_dd']:.1%}")
    if r22["return"] > bnh22["return"]:
        print("→ Strategy outperformed in 2022 (defensive value)")
    else:
        print("→ Strategy underperformed in 2022")

    # 3. SPY (less volatile)
    print("\n--- 3. SPY 3Y (Less Volatile) ---")
    rspy = run_strategy("SPY", "3y")
    bnh_spy = buy_hold_stats("SPY", start_3y.strftime("%Y-%m-%d"), end_3y.strftime("%Y-%m-%d"))
    print(f"Strategy:  Return={rspy['return']:.1%}  MaxDD={rspy['max_dd']:.1%}  Trades={rspy['n_trades']}")
    print(f"B&H SPY:   Return={bnh_spy['return']:.1%}  MaxDD={bnh_spy['max_dd']:.1%}")
    print(f"→ Alpha vs SPY: {rspy['return'] - bnh_spy['return']:.1%}")

    # 4. Summary
    print("\n" + "=" * 60)
    print("SUMMARY (Gemini's Questions)")
    print("=" * 60)
    print(f"1. Max DD Strategy vs B&H: {r3['max_dd']:.1%} vs {bnh3['max_dd']:.1%} → DD advantage: {abs(bnh3['max_dd']) - abs(r3['max_dd']):.1%} pts")
    print(f"2. Avg Trade: {r3['avg_trade_pct']:.3f}%  {'⚠️ <0.5% → slippage concern' if r3['avg_trade_pct'] < 0.5 else '✓ OK'}")
    print(f"3. 2022: Strategy {r22['return']:.1%} vs B&H {bnh22['return']:.1%}")
    print(f"4. SPY: Alpha = {rspy['return'] - bnh_spy['return']:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    main()
