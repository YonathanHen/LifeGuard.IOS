#!/usr/bin/env python
"""
Slippage Sensitivity — ניתוח רגישות לעלויות (Gemini's suggestion)
מריץ backtest עם רמות שונות של commission + slippage כדי למצוא:
- Gross return (0 costs) — הרווח "הגולמי" לפני חיכוך
- Breakeven point — באיזו רמת עלויות האסטרטגיה מפסידה
- התרשמות: האם השיפור צריך לבוא מפחות טריידים או מעלויות נמוכות יותר

Usage: python slippage_sensitivity.py [--quick]
  --quick  fewer scenarios, 2y period (faster, ~4 min)
"""
import sys
import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine


# תרחישי עלויות: (commission_bps, slippage_bps) | round-trip = 2*(comm+slipp) bps
SCENARIOS_FULL = [
    (0, 0, "Zero costs (gross)"),
    (2, 2, "Cheap broker (2+2 bps)"),
    (5, 3, "Baseline (5+3 bps)"),
    (8, 5, "Moderate retail (8+5)"),
    (10, 8, "Retail+ (10+8)"),
    (15, 10, "Expensive (15+10)"),
    (20, 15, "Worst case (20+15)"),
]
SCENARIOS_QUICK = [(0, 0, "Zero (gross)"), (5, 3, "Baseline 5+3"), (15, 10, "Expensive")]


def run_one(comm: float, slipp: float, period: str = "3y") -> dict:
    """Run backtest with given costs, return key metrics."""
    engine = BacktestEngine(
        symbol="AAPL",
        horizon="daily",
        refit_every=5,
        use_ml=False,
        commission_bps=comm,
        slippage_bps=slipp,
    )
    r = engine.run(period=period)
    rt_bps = 2 * (comm + slipp)
    avg_pct = (r.total_return / r.n_trades * 100) if r.n_trades else 0
    cost_per_trade_pct = rt_bps / 100  # 16 bps = 0.16%
    return {
        "return": r.total_return,
        "sharpe": r.sharpe_ratio,
        "max_dd": r.max_drawdown,
        "n_trades": r.n_trades,
        "avg_trade_pct": avg_pct,
        "rt_bps": rt_bps,
        "cost_per_trade_pct": cost_per_trade_pct,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="Fewer scenarios, 1y period (faster)")
    args = ap.parse_args()

    quick = args.quick
    scenarios = SCENARIOS_QUICK if quick else SCENARIOS_FULL
    period = "2y" if quick else "3y"

    print("=" * 70)
    print("SLIPPAGE SENSITIVITY — ניתוח רגישות לעלויות (Gemini)")
    print("=" * 70)
    print(f"Period: {period}  |  Round-trip = 2×(comm+slipp) bps")
    print()

    results = []
    for i, (comm, slipp, label) in enumerate(scenarios):
        print(f"  Running {i+1}/{len(scenarios)}: {label}...", flush=True)
        d = run_one(comm, slipp, period=period)
        d["label"] = label
        results.append(d)

    print(f"{'Scenario':<28} {'Return':>10} {'Avg/Trade':>10} {'Trades':>8} {'Net vs Cost':>12}")
    print("-" * 70)
    for d in results:
        net_vs_cost = "OK" if d["avg_trade_pct"] > d["cost_per_trade_pct"] else "⚠️ BURN"
        print(f"{d['label']:<28} {d['return']:>9.1%} {d['avg_trade_pct']:>9.3f}% {d['n_trades']:>8} {net_vs_cost:>12}")

    # Find breakeven
    print("\n" + "=" * 70)
    print("BREAKEVEN ANALYSIS")
    print("=" * 70)

    r0 = results[0]
    gross_ret = r0["return"]
    gross_avg = r0["avg_trade_pct"]
    n = r0["n_trades"]

    # Approximate: return ≈ gross - n_trades * (cost_per_trade_pct/100)
    # Breakeven: cost_per_trade_pct = gross_ret/n_trades * 100
    breakeven_rt_bps = gross_avg * 100  # avg trade in bps ≈ max round-trip we can afford
    breakeven_rt_pct = breakeven_rt_bps / 100
    print(f"Gross return (0 costs): {gross_ret:.1%}")
    print(f"Gross avg/trade:         {gross_avg:.3f}% ({gross_avg*100:.2f} bps)")
    print(f"Breakeven round-trip:    ~{breakeven_rt_bps:.0f} bps  (when avg_trade ≈ cost_per_trade)")
    cost_16 = 2 * (5 + 3)
    print(f"Current (5+3=16 bps):   Cost {cost_16} bps {'>' if cost_16 > breakeven_rt_bps else '<'} breakeven ~{breakeven_rt_bps:.0f} → ", end="")
    print("negative expectancy" if cost_16 > breakeven_rt_bps else "positive expectancy")

    # First negative return
    neg = [d for d in results if d["return"] <= 0]
    if neg:
        first_neg = neg[0]
        print(f"\nFirst negative return at: {first_neg['label']} (RT={first_neg['rt_bps']} bps)")
    else:
        print("\nAll tested scenarios have positive return (costs not high enough to flip)")

    print("\n" + "=" * 70)
    print("GEMINI TAKEAWAY")
    print("=" * 70)
    print("• אם avg/trade < cost_per_trade → כל טרייד 'שורף' כסף (מוות ב-1000 חתכים)")
    print("• כדי לשרוד במסחר אמיתי: צריך avg_trade ≥ 0.5% (~50 bps round-trip)")
    print("• דרכים: ML filter (פחות טריידים, איכות גבוהה) | הוצאת יציאה מרווחת (let winners run)")
    print("• ניתוח ML filter: python scripts/min_gain_filter.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
