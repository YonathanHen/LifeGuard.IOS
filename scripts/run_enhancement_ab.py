#!/usr/bin/env python
"""
Compare Stat Core baseline vs recommended enhancement flags (see docs/RECOMMENDED_ENHANCEMENTS_AB.md).

Usage:
  python scripts/run_enhancement_ab.py --battery helpful --period 3y --json-out storage/enhancement_ab_helpful.json
  python scripts/run_enhancement_ab.py --battery full --period 3y --symbol AAPL --with-ml
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from backtesting.engine import BacktestEngine


def _row(name: str, r) -> dict:
    return {
        "scenario": name,
        "sharpe": round(r.sharpe_ratio, 4),
        "max_dd": round(r.max_drawdown, 4),
        "total_return": round(r.total_return, 4),
        "n_trades": r.n_trades,
        "hit_rate": round(r.hit_rate, 4),
        "exposure_pct": round(r.exposure_pct, 2),
    }


def main():
    ap = argparse.ArgumentParser(description="A/B: baseline vs roadmap enhancements")
    ap.add_argument("--symbol", default="AAPL")
    ap.add_argument("--period", default="3y")
    ap.add_argument("--with-ml", action="store_true", help="Use Stat+ML neg filter for all rows")
    ap.add_argument("--disaster-threshold", type=float, default=0.80)
    ap.add_argument("--json-out", type=str, default=None, help="Save results JSON")
    ap.add_argument(
        "--fast",
        action="store_true",
        help="refit_every=10 — quicker approximate run (for CI / smoke)",
    )
    ap.add_argument(
        "--battery",
        choices=("full", "helpful"),
        default="full",
        help="full=all scenarios | helpful=baseline + dual_momentum + low_vol + both (recommended next step)",
    )
    args = ap.parse_args()

    commission, slippage = 5.0, 3.0
    base_kw = dict(
        symbol=args.symbol,
        horizon="daily",
        refit_every=10 if args.fast else 5,
        commission_bps=commission,
        slippage_bps=slippage,
        use_ml=args.with_ml,
        ml_negative_filter=True if args.with_ml else False,
        ml_disaster_threshold=args.disaster_threshold,
    )

    full_scenarios = [
        ("baseline", {}),
        ("dual_momentum_spy", {"dual_momentum": True}),
        ("short_term_reversal", {"short_term_reversal": True}),
        ("low_vol_tilt", {"low_vol_tilt": True}),
        ("momentum_12_1_symbol", {"momentum_12_1_filter": True}),
        (
            "all_enhancements",
            {
                "dual_momentum": True,
                "short_term_reversal": True,
                "low_vol_tilt": True,
                "momentum_12_1_filter": True,
            },
        ),
    ]
    helpful_scenarios = [
        ("baseline", {}),
        ("dual_momentum_spy", {"dual_momentum": True}),
        ("low_vol_tilt", {"low_vol_tilt": True}),
        (
            "low_vol_tilt_and_dual_momentum",
            {"low_vol_tilt": True, "dual_momentum": True},
        ),
    ]
    scenarios = helpful_scenarios if args.battery == "helpful" else full_scenarios

    rows = []
    print("SignalFlow — Enhancement A/B (Stat" + ("+ML" if args.with_ml else "") + ")")
    print(f"  {args.symbol} | {args.period} | costs 5+3 bps\n")
    print(f"{'Scenario':<28} {'Sharpe':>8} {'MaxDD':>9} {'TotRet':>9} {'Trades':>7} {'Hit':>7} {'Exp%':>6}")
    print("-" * 88)

    for name, extra in scenarios:
        eng = BacktestEngine(**{**base_kw, **extra})
        r = eng.run(period=args.period)
        rows.append(_row(name, r))
        print(
            f"{name:<28} {r.sharpe_ratio:8.3f} {r.max_drawdown:8.1%} {r.total_return:8.1%} "
            f"{r.n_trades:7d} {r.hit_rate:6.1%} {r.exposure_pct:5.1f}%"
        )

    baseline = rows[0]
    print("-" * 88)
    print("Delta vs baseline (Sharpe / TotRet):")
    for row in rows[1:]:
        ds = row["sharpe"] - baseline["sharpe"]
        dr = row["total_return"] - baseline["total_return"]
        print(f"  {row['scenario']:<26} Sharpe {ds:+.3f}  Return {dr:+.1%}")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"symbol": args.symbol, "period": args.period, "with_ml": args.with_ml, "rows": rows}, f, indent=2)
        print(f"\nSaved {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
