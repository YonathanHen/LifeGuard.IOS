#!/usr/bin/env python
"""
SignalFlow — Multi-Stock Universe Backtest

Default: **best_combo** (mean_rev_mult, ATR, vol_target) — same as before.

Optional **--profile production**: same engine defaults as `run_backtest_with_ml.py`
(Stat+ML negative filter, optional --low-vol-tilt / --dual-momentum).

Usage:
  python scripts/run_multi_universe.py
  python scripts/run_multi_universe.py --period 3y --end-date 2026-03-02
  python scripts/run_multi_universe.py --profile production --period 3y --limit 10 --low-vol-tilt
  python scripts/run_multi_universe.py --profile production --no-ml --limit 5
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine


def _load_universe() -> list:
    config = Path(__file__).parent.parent / "config" / "symbols.yaml"
    if not config.exists():
        return ["AAPL", "MSFT", "GOOGL", "SPY"]
    try:
        import yaml
        with open(config, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("universe", data.get("primary", ["AAPL", "MSFT", "GOOGL", "SPY"]))
    except Exception:
        return ["AAPL", "MSFT", "GOOGL", "SPY"]


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Multi-Universe Backtest")
    ap.add_argument("--period", default="3y", help="Backtest period")
    ap.add_argument("--end-date", default=None, help="End date YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=None, help="Limit symbols (e.g. 10 for quick test)")
    ap.add_argument("--out", default=None, help="Save JSON path")
    ap.add_argument(
        "--profile",
        choices=("best_combo", "production"),
        default="best_combo",
        help="best_combo=legacy engine params | production=Stat+ML like run_backtest_with_ml",
    )
    ap.add_argument(
        "--no-ml",
        action="store_true",
        help="With --profile production: Stat only (no LSTM). Ignored for best_combo.",
    )
    ap.add_argument(
        "--disaster-threshold",
        type=float,
        default=0.80,
        help="production profile: P(down) block threshold (default 0.80)",
    )
    ap.add_argument("--low-vol-tilt", action="store_true", help="BacktestEngine low_vol_tilt (any profile)")
    ap.add_argument("--dual-momentum", action="store_true", help="BacktestEngine dual_momentum (any profile)")
    args = ap.parse_args()

    symbols = _load_universe()
    if args.limit:
        symbols = symbols[: args.limit]

    print("=" * 60)
    print("SignalFlow — Multi-Universe Backtest")
    print("=" * 60)
    profile_note = f"profile={args.profile}"
    if args.profile == "production" and args.no_ml:
        profile_note += " Stat-only"
    if args.low_vol_tilt:
        profile_note += " +low_vol_tilt"
    if args.dual_momentum:
        profile_note += " +dual_momentum"
    print(
        f"Universe: {len(symbols)} symbols | Period: {args.period} | {profile_note}"
        + (f" | End: {args.end_date}" if args.end_date else "")
    )

    if args.profile == "best_combo":
        engine_kw = {
            "horizon": "daily",
            "use_ml": False,
            "mean_rev_mult": 2.0,
            "atr_stop_mult": 2.0,
            "vol_target_ann": 0.15,
            "commission_bps": 5,
            "slippage_bps": 3,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
        }
    else:
        engine_kw = {
            "horizon": "daily",
            "use_ml": not args.no_ml,
            "ml_threshold": 0.6,
            "ml_negative_filter": True,
            "ml_disaster_threshold": args.disaster_threshold,
            "mean_rev_mult": 1.0,
            "atr_stop_mult": 0.0,
            "vol_target_ann": None,
            "commission_bps": 5,
            "slippage_bps": 3,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
        }

    results = []
    for sym in symbols:
        try:
            eng = BacktestEngine(**{**engine_kw, "symbol": sym})
            r = eng.run(period=args.period, end_date=args.end_date)
            results.append({"symbol": sym, "sharpe": r.sharpe_ratio, "return": r.total_return, "dd": r.max_drawdown, "trades": r.n_trades})
            print(f"  {sym}: Sharpe={r.sharpe_ratio:.3f} Return={r.total_return:.1%} DD={r.max_drawdown:.1%}")
        except Exception as e:
            print(f"  {sym}: ERROR {e}")
            results.append({"symbol": sym, "error": str(e)})

    ok = [x for x in results if "error" not in x]
    if ok:
        ret_avg = sum(x["return"] for x in ok) / len(ok)
        sharpe_avg = sum(x["sharpe"] for x in ok) / len(ok)
        dd_avg = sum(x["dd"] for x in ok) / len(ok)
        print(f"\n--- Aggregate ({len(ok)} symbols) ---")
        print(f"Avg Return: {ret_avg:.1%} | Avg Sharpe: {sharpe_avg:.3f} | Avg DD: {dd_avg:.1%}")

    if args.out:
        payload = {
            "results": results,
            "period": args.period,
            "end_date": args.end_date,
            "profile": args.profile,
            "no_ml": args.no_ml,
            "disaster_threshold": args.disaster_threshold if args.profile == "production" else None,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
            "run_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nSaved: {args.out}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
