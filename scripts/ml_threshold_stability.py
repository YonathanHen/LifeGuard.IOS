#!/usr/bin/env python
"""
ML Threshold Stability — וידוא שה-Threshold לא Overfitting (Gemini)

מריץ backtest עם סף אופטימלי (למשל 0.85) על נכסים נוספים (MSFT, GOOGL)
כדי לוודא שזה כלל אצבע שעובד, לא רק על AAPL.

אם זה עובד גם שם — מערכת מוכנה ל-Paper Trading.
"""
import sys
import argparse
import warnings
import time
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine

DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL"]
COST_PER_TRADE_PCT = 0.16  # 5+3 bps round-trip
SLIPPAGE_SAFE_PCT = 0.5


def lstm_available() -> bool:
    try:
        from models.ml.lstm_model import LSTMPredictor
        return LSTMPredictor(lookback=40).load()
    except Exception:
        return False


def run_one(symbol: str, threshold: float, period: str) -> dict:
    engine = BacktestEngine(
        symbol=symbol,
        horizon="daily",
        refit_every=5,
        use_ml=True,
        ml_threshold=threshold,
        ml_negative_filter=False,
        commission_bps=5,
        slippage_bps=3,
    )
    r = engine.run(period=period)
    avg = (r.total_return / r.n_trades * 100) if r.n_trades else 0
    return {
        "symbol": symbol,
        "return": r.total_return,
        "sharpe": r.sharpe_ratio,
        "max_dd": r.max_drawdown,
        "n_trades": r.n_trades,
        "avg_trade_pct": avg,
        "safe_vs_cost": avg >= COST_PER_TRADE_PCT,
        "safe_vs_slippage": avg >= SLIPPAGE_SAFE_PCT,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.85,
        help="ML threshold (P_up >= X). Default 0.85 = Sweet Spot from min_gain_filter.")
    ap.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated symbols (default: AAPL,MSFT,GOOGL)")
    ap.add_argument("--period", type=str, default="3y", help="Backtest period (default: 3y)")
    args = ap.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        symbols = DEFAULT_SYMBOLS

    if not lstm_available():
        print("מודל LSTM לא נמצא. הרץ: python scripts/train_lstm.py")
        return

    print("=" * 70)
    print("ML THRESHOLD STABILITY — וידוא שלא Overfitting (Gemini)")
    print("=" * 70)
    print("Threshold: P_up >= {:.2f}  |  Period: {}  |  נכסים: {}".format(args.threshold, args.period, ", ".join(symbols)))
    print()

    results = []
    for i, sym in enumerate(symbols):
        print(f"  Running {i+1}/{len(symbols)}: {sym}...", flush=True)
        try:
            d = run_one(sym, args.threshold, args.period)
            results.append(d)
        except Exception as e:
            print(f"    ⚠️ {sym} failed: {e}")
            results.append({"symbol": sym, "n_trades": 0, "return": 0, "sharpe": 0, "max_drawdown": 0, "avg_trade_pct": 0, "safe_vs_cost": False})
        if i < len(symbols) - 1:
            time.sleep(8)  # Avoid Yahoo rate limit between symbols

    print()
    print(f"{'Symbol':<8} {'Trades':>8} {'Return':>10} {'Avg/Trade':>10} {'MaxDD':>10} {'Safe?':>8}")
    print("-" * 60)
    for d in results:
        safe = "✓" if d.get("safe_vs_cost", False) else "⚠️"
        nt = d.get("n_trades", 0)
        if nt == 0:
            print(f"{d['symbol']:<8} {'FAIL':>8} {'-':>9} {'-':>10} {'-':>10} {safe:>8}")
        else:
            print(f"{d['symbol']:<8} {nt:>8} {d['return']:>9.1%} {d['avg_trade_pct']:>9.3f}% {d['max_drawdown']:>9.1%} {safe:>8}")

    ok = sum(1 for d in results if d["safe_vs_cost"])
    print("\n" + "=" * 70)
    print("מסקנה")
    print("=" * 70)
    if ok == len(results):
        print("✓ Threshold {:.2f} יציב על כל הנכסים — מוכן ל-Paper Trading".format(args.threshold))
    elif ok > 0:
        print("~ Threshold {:.2f} עובד על חלק מהנכסים. שקול התאמה או נכסים ספציפיים.".format(args.threshold))
    else:
        print("⚠️ Threshold {:.2f} לא עומד ב-safe על אף נכס. נסה סף נמוך יותר או אימון מחדש.".format(args.threshold))
    print("=" * 70)


if __name__ == "__main__":
    main()
