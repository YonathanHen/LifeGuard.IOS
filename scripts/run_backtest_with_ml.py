#!/usr/bin/env python
"""
SignalFlow — Backtest with ML: Stat vs Stat+ML
Runs backtest, compares performance, Threshold Stability (±0.02), Regime Sensitivity.
Outputs: Sharpe, Drawdown, Exposure, Decision Density, Equity Curve (optional plot).
"""
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from backtesting.engine import BacktestEngine, BacktestResult


def _print_result(name: str, r: BacktestResult, verbose: bool = True):
    """Print backtest result."""
    print(f"\n--- {name} ---")
    print(f"  Sharpe:      {r.sharpe_ratio:.3f}")
    print(f"  Max DD:      {r.max_drawdown:.1%}")
    print(f"  Total Ret:   {r.total_return:.1%}")
    print(f"  N Trades:    {r.n_trades}")
    print(f"  Hit Rate:    {r.hit_rate:.1%}")
    print(f"  Exposure:    {r.exposure_pct:.1f}%")
    if verbose and r.by_regime:
        print("  By Regime:")
        for rname, sub in r.by_regime.items():
            print(f"    {rname}: Sharpe={sub.sharpe_ratio:.2f} DD={sub.max_drawdown:.1%} Trades={sub.n_trades}")


def _read_model_meta() -> dict:
    """Read LSTM model metadata (lookback etc.) from storage."""
    meta_path = Path(__file__).parent.parent / "storage" / "lstm_model.json"
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_backtest_run(
    params: dict,
    r_stat: BacktestResult,
    r_ml: BacktestResult | None,
    registry_path: Path,
    label: str | None,
):
    """Append run to storage/backtest_runs.json."""
    meta = _read_model_meta()
    entry = {
        "date": datetime.utcnow().isoformat() + "Z",
        "label": label or "",
        "params": params,
        "model": {"lookback": meta.get("lookback"), "n_features": meta.get("n_features"), "train_date": meta.get("train_date")},
        "stat": {
            "sharpe": round(r_stat.sharpe_ratio, 4),
            "max_dd": round(r_stat.max_drawdown, 4),
            "total_return": round(r_stat.total_return, 4),
            "n_trades": r_stat.n_trades,
            "hit_rate": round(r_stat.hit_rate, 4),
            "exposure_pct": round(r_stat.exposure_pct, 2),
        },
        "stat_ml": None,
    }
    if r_ml is not None:
        entry["stat_ml"] = {
            "sharpe": round(r_ml.sharpe_ratio, 4),
            "max_dd": round(r_ml.max_drawdown, 4),
            "total_return": round(r_ml.total_return, 4),
            "n_trades": r_ml.n_trades,
            "hit_rate": round(r_ml.hit_rate, 4),
            "exposure_pct": round(r_ml.exposure_pct, 2),
        }
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if registry_path.exists():
        try:
            with open(registry_path) as f:
                data = json.load(f)
        except Exception:
            pass
    runs = data.get("runs", [])
    runs.append(entry)
    data["runs"] = runs
    data["_last_updated"] = entry["date"]
    with open(registry_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n[Saved run to {registry_path}]")


def _decision_density(r: BacktestResult, period_years: float) -> dict:
    """Compute N Trades/Year, Avg Days in Trade, Avg Return per Trade."""
    n_trades = r.n_trades
    n_days = r.n_days
    if n_days <= 0 or period_years <= 0:
        return {"trades_per_year": 0, "avg_days_in_trade": 0, "avg_return_per_trade": 0}
    trades_per_year = n_trades / period_years
    # Approximate avg days in trade: total long-days / number of "entries" (simplified: n_trades as proxy for entries)
    long_days = int(r.exposure_pct / 100 * n_days)
    avg_days = long_days / n_trades if n_trades > 0 else 0
    avg_ret = r.total_return / n_trades if n_trades > 0 else 0
    return {
        "trades_per_year": trades_per_year,
        "avg_days_in_trade": avg_days,
        "avg_return_per_trade": avg_ret,
    }


def main():
    ap = argparse.ArgumentParser(description="SignalFlow Backtest: Stat vs Stat+ML")
    ap.add_argument("--period", default="3y", help="Backtest period (default 3y)")
    ap.add_argument("--symbol", default="AAPL", help="Symbol")
    ap.add_argument("--horizon", choices=["daily", "weekly", "regime_outlook"], default="daily", help="Horizon (default daily). ML only for daily.")
    ap.add_argument("--no-ml", action="store_true", help="Run Stat only (no ML comparison)")
    ap.add_argument("--no-costs", action="store_true", help="Disable commission/slippage")
    ap.add_argument("--stability", action="store_true", help="Run threshold stability (pre-compute once)")
    ap.add_argument("--stability-start", type=float, default=0.50, help="Stability range start (default 0.50)")
    ap.add_argument("--stability-end", type=float, default=0.70, help="Stability range end (default 0.70)")
    ap.add_argument("--stability-step", type=float, default=0.02, help="Stability step (default 0.02)")
    ap.add_argument("--no-negative-filter", action="store_true", help="Use legacy AND mode instead of Negative Filter (default: Negative Filter)")
    ap.add_argument("--disaster-threshold", type=float, default=0.80, help="Negative Filter: block when P(down) > this (default 0.80)")
    ap.add_argument("--save-equity", type=str, help="Save equity curves to CSV")
    ap.add_argument("--label", type=str, help="Label for saved run (e.g. legacy_and_61pct)")
    ap.add_argument("--plot", action="store_true", help="Plot equity curve comparison (requires matplotlib)")
    ap.add_argument(
        "--low-vol-tilt",
        action="store_true",
        help="Scale position x0.5 when realized vol in top quartile (60d). See RESEARCH_DECISIONS_LOG.md",
    )
    ap.add_argument(
        "--dual-momentum",
        action="store_true",
        help="Go flat when SPY 12m return < ~risk-free (see models/rules/dual_momentum.py)",
    )
    args = ap.parse_args()

    commission = 0.0 if args.no_costs else 5.0
    slippage = 0.0 if args.no_costs else 3.0

    years = float(args.period.replace("y", "").replace("Y", "")) if "y" in args.period.lower() else 3.0

    print("=" * 65)
    print("SignalFlow — Backtest with ML")
    print("=" * 65)
    extras = []
    if args.low_vol_tilt:
        extras.append("low_vol_tilt")
    if args.dual_momentum:
        extras.append("dual_momentum")
    extra_s = f" | Extras: {','.join(extras)}" if extras else ""
    print(f"Symbol: {args.symbol} | Period: {args.period} | Horizon: {args.horizon} | Costs: {'off' if args.no_costs else '5+3 bps'}{extra_s}")

    eng_kw = dict(
        commission_bps=commission,
        slippage_bps=slippage,
        low_vol_tilt=args.low_vol_tilt,
        dual_momentum=args.dual_momentum,
    )

    # Stat only
    engine_stat = BacktestEngine(
        symbol=args.symbol,
        horizon=args.horizon,
        use_ml=False,
        **eng_kw,
    )
    r_stat = engine_stat.run(period=args.period)
    _print_result("Stat Core only", r_stat)

    if args.horizon != "daily" and not args.no_ml:
        print("\n[ML only for daily horizon — use --horizon daily for Stat+ML]")

    if not args.no_ml and args.horizon == "daily":
        neg_filter = not args.no_negative_filter  # Default: Negative Filter (Sweet spot 0.80)
        engine_ml = BacktestEngine(
            symbol=args.symbol,
            horizon=args.horizon,
            use_ml=True,
            ml_threshold=0.6,
            ml_negative_filter=neg_filter,
            ml_disaster_threshold=args.disaster_threshold,
            **eng_kw,
        )
        ml_label = f"Stat + ML (neg filter P_down>{args.disaster_threshold})" if neg_filter else "Stat + ML (0.60)"

        if args.stability:
            import numpy as np
            import statistics
            if neg_filter:
                # Negative filter: vary disaster_threshold (P_down), default 0.75-0.85 step 0.05
                st_start, st_end, st_step = 0.75, 0.85, 0.05
                thresholds = np.arange(st_start, st_end + st_step / 2, st_step).tolist()
                thresholds = [round(t, 2) for t in thresholds]
                if args.disaster_threshold not in thresholds:
                    thresholds = sorted(set(thresholds + [args.disaster_threshold]))
                primary_th = args.disaster_threshold
                col_name = "DisasterTh"
            else:
                thresholds = np.arange(
                    args.stability_start,
                    args.stability_end + args.stability_step / 2,
                    args.stability_step,
                ).tolist()
                thresholds = [round(t, 2) for t in thresholds]
                if 0.6 not in thresholds:
                    thresholds = sorted(set(thresholds + [0.6]))
                primary_th = 0.6
                col_name = "Threshold"
            print(f"\n--- {'Disaster Threshold' if neg_filter else 'Threshold'} Stability ({len(thresholds)} steps) ---")
            print("Pre-compute once -> fast run over all thresholds")
            print()
            df_stability, r_ml, st_cache = engine_ml.run_stability(
                period=args.period, thresholds=thresholds, primary_threshold=primary_th
            )
            # Rename Threshold col for negative filter clarity
            if neg_filter and "Threshold" in df_stability.columns:
                df_stability = df_stability.rename(columns={"Threshold": col_name})
            print(df_stability.to_string(index=False))
            print()
            if r_ml is None:
                r_ml = engine_ml.run(period=args.period)
            _print_result(ml_label, r_ml)
            # Plateau / Peak / Cliff
            sharpes = df_stability["Sharpe"].tolist()
            trades = df_stability["Trades"].tolist()
            if len(sharpes) >= 2:
                sharpe_std = statistics.stdev(sharpes)
                med = statistics.median(sharpes)
                best_sharpe = max(sharpes)
                if sharpe_std < 0.2:
                    print("  [OK] Plateau: stable results - robust model")
                elif best_sharpe > med + 0.5:
                    print("  [!!] The Peak: single threshold with outlier Sharpe - check overfitting")
                if min(trades) < 10 and max(trades) > 50:
                    print("  [!!] The Cliff: trades drop at some thresholds - model too selective")
                if df_stability["Exposure"].min() < 10:
                    print("  [!!] Exposure < 10% - consider lower threshold (e.g. 0.55)")
            # Error Type Analysis (reuses cache from stability - no extra precompute)
            dec, rets, ref = st_cache
            err = engine_ml.error_type_analysis(
                period=args.period,
                ml_threshold=0.6,
                disaster_threshold=args.disaster_threshold if neg_filter else None,
                decisions=dec, next_returns=rets, refit_every=ref,
            )
            th_desc = f"P_down>{args.disaster_threshold}" if neg_filter else "0.60"
            print()
            print(f"--- Error Type (Stat Long, ML blocked @ {th_desc}) ---")
            print(f"  Saved Losses (ML blocked, price fell):      {err['saved_losses']}")
            print(f"  Missed Opportunities (ML blocked, price rose): {err['missed_opportunities']}")
            print(f"  Sum Saved (losses avoided):                 {err['sum_saved']:.4f} ({err['sum_saved']*100:.2f}%)")
            print(f"  Sum Missed (gains forgone):                  {err['sum_missed']:.4f} ({err['sum_missed']*100:.2f}%)")
            print(f"  Net EV of ML Filter (saved - missed):       {err['net_ev']:.4f} ({err['net_ev']*100:.2f}%)")
            if err['saved_losses']:
                print(f"  Mean blocked loss (avg loss avoided):      {err['mean_blocked_loss']*100:.2f}%")
            if err['missed_opportunities']:
                print(f"  Mean missed gain (avg gain forgone):       {err['mean_missed_gain']*100:.2f}%")
        else:
            r_ml = engine_ml.run(period=args.period)
            _print_result(ml_label, r_ml)

        # Decision Density
        d_stat = _decision_density(r_stat, years)
        d_ml = _decision_density(r_ml, years)
        print("\n--- Decision Density ---")
        print(f"  Stat:     {d_stat['trades_per_year']:.1f} trades/yr | {d_stat['avg_days_in_trade']:.1f} avg days | {d_stat['avg_return_per_trade']*100:.2f}% avg ret/trade")
        print(f"  Stat+ML:  {d_ml['trades_per_year']:.1f} trades/yr | {d_ml['avg_days_in_trade']:.1f} avg days | {d_ml['avg_return_per_trade']*100:.2f}% avg ret/trade")

        # Save equity curve
        if args.save_equity:
            import pandas as pd
            n = min(len(r_stat.equity_curve), len(r_ml.equity_curve))
            df = pd.DataFrame({
                "stat": r_stat.equity_curve.values[:n],
                "stat_ml": r_ml.equity_curve.values[:n],
            })
            df.to_csv(args.save_equity, index=False)
            print(f"\nEquity curves saved to {args.save_equity}")

        # Plot
        if args.plot:
            try:
                import matplotlib.pyplot as plt
                import pandas as pd
                n = min(len(r_stat.equity_curve), len(r_ml.equity_curve))
                plt.figure(figsize=(10, 5))
                plt.plot(r_stat.equity_curve.values[:n], label="Stat Core", alpha=0.8)
                plt.plot(r_ml.equity_curve.values[:n], label="Stat + ML", alpha=0.8)
                plt.xlabel("Trading Day")
                plt.ylabel("Equity (1 = start)")
                plt.legend()
                plt.title(f"SignalFlow Backtest: {args.symbol} ({args.period})")
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                out_path = Path(args.save_equity).with_suffix(".png") if args.save_equity else "equity_curve.png"
                plt.savefig(out_path)
                print(f"Plot saved to {out_path}")
            except ImportError:
                print("matplotlib not installed — skip --plot")

        # Auto-save every run
        neg_filter = not args.no_negative_filter
        params = {
            "symbol": args.symbol,
            "period": args.period,
            "horizon": args.horizon,
            "commission_bps": commission,
            "slippage_bps": slippage,
            "mode": "negative_filter" if neg_filter else "legacy_and",
            "disaster_threshold": args.disaster_threshold if neg_filter else None,
            "ml_threshold": 0.6,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
        }
        registry_path = Path(__file__).parent.parent / "storage" / "backtest_runs.json"
        _save_backtest_run(params, r_stat, r_ml, registry_path, args.label)
    else:
        # Auto-save (Stat only)
        params = {
            "symbol": args.symbol,
            "period": args.period,
            "horizon": args.horizon,
            "commission_bps": commission,
            "slippage_bps": slippage,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
        }
        registry_path = Path(__file__).parent.parent / "storage" / "backtest_runs.json"
        _save_backtest_run(params, r_stat, None, registry_path, args.label)

    print("\n" + "=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
