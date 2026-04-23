#!/usr/bin/env python
"""
Minimum Gain Filter — ניתוח איכותי (Gemini)

בודק: "מה היה קורה לרווח הסופי אם היינו מבטלים את כל הטריידים
שבהם מודל ה-ML חזה רווח נמוך מ-X?" (P_up < X)

מאפשר למצוא את ה-Sweet Spot:
- מספר טריידים יורד (פחות עמלות)
- רווח ממוצע לטרייד קופץ מעל סף ה-Slippage (0.5%)

Implementation: משתמש ב-ml_threshold — רק טריידים עם P_up >= X.

Usage:
  python scripts/min_gain_filter.py --thresholds 0.5,0.6,0.7,0.8,0.85
  python scripts/min_gain_filter.py --quick
  python scripts/min_gain_filter.py --symbol MSFT --thresholds 0.7,0.8,0.85
"""
import sys
import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine

# סף ה-Slippage — צריך avg_trade >= זה כדי לשרוד במסחר אמיתי
SLIPPAGE_SAFE_AVG_PCT = 0.5
COST_PER_TRADE_BPS = 16  # 5+3 round-trip
COST_PER_TRADE_PCT = COST_PER_TRADE_BPS / 100


def lstm_available() -> bool:
    """Check if LSTM model is trained and loadable."""
    try:
        from models.ml.lstm_model import LSTMPredictor
        lstm = LSTMPredictor(lookback=40)
        return lstm.load()
    except Exception:
        return False


def run_one(threshold: float, symbol: str = "AAPL", period: str = "3y") -> dict:
    """Run backtest with ML filter at given P_up threshold."""
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
    avg_pct = (r.total_return / r.n_trades * 100) if r.n_trades else 0
    return {
        "threshold": threshold,
        "symbol": symbol,
        "return": r.total_return,
        "sharpe": r.sharpe_ratio,
        "max_dd": r.max_drawdown,
        "n_trades": r.n_trades,
        "avg_trade_pct": avg_pct,
        "hit_rate": r.hit_rate,
        "safe_vs_slippage": avg_pct >= SLIPPAGE_SAFE_AVG_PCT,
        "safe_vs_cost": avg_pct >= COST_PER_TRADE_PCT,
    }


def main():
    ap = argparse.ArgumentParser(
        epilog="Example: python min_gain_filter.py --thresholds 0.5,0.6,0.7,0.8,0.85"
    )
    ap.add_argument("--quick", action="store_true", help="Fewer thresholds, 2y period (faster)")
    ap.add_argument("--thresholds", type=str, default=None,
        help="Comma-separated thresholds (e.g. 0.5,0.6,0.7,0.8,0.85). Overrides --quick.")
    ap.add_argument("--symbol", type=str, default="AAPL", help="Symbol to test (default: AAPL)")
    ap.add_argument("--period", type=str, default=None, help="Period (2y, 3y). Default: 2y if --quick else 3y")
    args = ap.parse_args()

    if args.period:
        period = args.period
    else:
        period = "2y" if args.quick and not args.thresholds else "3y"

    if args.thresholds:
        thresholds = [float(x.strip()) for x in args.thresholds.split(",") if x.strip()]
    else:
        thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90] if not args.quick else [0.50, 0.60, 0.70, 0.80, 0.90]

    if not lstm_available():
        print("=" * 70)
        print("MINIMUM GAIN FILTER — דורש מודל LSTM מאומן")
        print("=" * 70)
        print("המודל לא נמצא. הרץ קודם:")
        print("  python scripts/train_lstm.py   (או scripts/train_hunter_model.py)")
        print()
        print("בינתיים — הרצת Stat-only (ללא ML) להשוואה:")
        r = BacktestEngine(symbol=args.symbol, horizon="daily", use_ml=False, commission_bps=5, slippage_bps=3).run(period=period)
        avg = (r.total_return / r.n_trades * 100) if r.n_trades else 0
        print(f"  Stat-only: {r.n_trades} trades, return={r.total_return:.1%}, avg/trade={avg:.3f}%")
        print("=" * 70)
        return

    print("=" * 70)
    print("MINIMUM GAIN FILTER — ניתוח איכותי (Gemini)")
    print("=" * 70)
    print("Filter: רק כניסות כאשר P_up >= X  |  Symbol: {}  |  Period: {}  |  Costs: 5+3 bps".format(args.symbol, period))
    print("מטרה: מציאת Sweet Spot — פחות טריידים, avg/trade >= {:.1f}%".format(SLIPPAGE_SAFE_AVG_PCT))
    print()

    results = []
    for i, th in enumerate(thresholds):
        print(f"  Running {i+1}/{len(thresholds)}: P_up >= {th:.2f}...", flush=True)
        d = run_one(th, symbol=args.symbol, period=period)
        results.append(d)

    print()
    print(f"{'P_up >=':>10} {'Trades':>8} {'Return':>10} {'Avg/Trade':>10} {'Safe?':>8}")
    print("-" * 50)
    for d in results:
        safe = "✓" if d["safe_vs_cost"] else "⚠️"
        print(f"{d['threshold']:>10.2f} {d['n_trades']:>8} {d['return']:>9.1%} {d['avg_trade_pct']:>9.3f}% {safe:>8}")

    # Sweet spot
    safe_results = [d for d in results if d["safe_vs_cost"]]
    print("\n" + "=" * 70)
    print("SWEET SPOT")
    print("=" * 70)
    if safe_results:
        best = max(safe_results, key=lambda x: x["return"])
        print(f"סף נמוך ביותר שעדיין safe vs cost (0.16%): P_up >= {best['threshold']:.2f}")
        print(f"  → {best['n_trades']} trades, return={best['return']:.1%}, avg={best['avg_trade_pct']:.3f}%")
    else:
        print("אין סף שמוביל ל-avg_trade >= 0.16% (עלויות round-trip)")
        print("נסה סף גבוה יותר (0.90+) או אופטימיזציה נוספת")
    print()
    print("• Safe vs Slippage (0.5%): avg_trade >= 0.5% — מומלץ למסחר אמיתי")
    print("• Safe vs Cost (0.16%):   avg_trade >= עלויות round-trip — מינימום לתקווה")
    print()
    print("בדיקת יציבות על נכסים נוספים: python scripts/ml_threshold_stability.py --threshold 0.85")
    print("=" * 70)


if __name__ == "__main__":
    main()
