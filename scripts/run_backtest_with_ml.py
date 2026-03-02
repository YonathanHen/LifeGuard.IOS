#!/usr/bin/env python
"""
SignalFlow — Backtest with ML: Stat vs Stat+ML
Runs backtest, compares performance, Threshold Stability (±0.02), Regime Sensitivity.
Outputs: Sharpe, Drawdown, Exposure, Decision Density, Equity Curve (optional plot).
"""
import sys
import argparse
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
    ap.add_argument("--no-ml", action="store_true", help="Run Stat only (no ML comparison)")
    ap.add_argument("--no-costs", action="store_true", help="Disable commission/slippage")
    ap.add_argument("--stability", action="store_true", help="Run threshold stability (pre-compute once)")
    ap.add_argument("--stability-start", type=float, default=0.50, help="Stability range start (default 0.50)")
    ap.add_argument("--stability-end", type=float, default=0.70, help="Stability range end (default 0.70)")
    ap.add_argument("--stability-step", type=float, default=0.02, help="Stability step (default 0.02)")
    ap.add_argument("--save-equity", type=str, help="Save equity curves to CSV")
    ap.add_argument("--plot", action="store_true", help="Plot equity curve comparison (requires matplotlib)")
    args = ap.parse_args()

    commission = 0.0 if args.no_costs else 5.0
    slippage = 0.0 if args.no_costs else 3.0

    years = float(args.period.replace("y", "").replace("Y", "")) if "y" in args.period.lower() else 3.0

    print("=" * 65)
    print("SignalFlow — Backtest with ML")
    print("=" * 65)
    print(f"Symbol: {args.symbol} | Period: {args.period} | Costs: {'off' if args.no_costs else '5+3 bps'}")

    # Stat only
    engine_stat = BacktestEngine(
        symbol=args.symbol,
        horizon="daily",
        use_ml=False,
        commission_bps=commission,
        slippage_bps=slippage,
    )
    r_stat = engine_stat.run(period=args.period)
    _print_result("Stat Core only", r_stat)

    if not args.no_ml:
        engine_ml = BacktestEngine(
            symbol=args.symbol,
            horizon="daily",
            use_ml=True,
            ml_threshold=0.6,
            commission_bps=commission,
            slippage_bps=slippage,
        )

        if args.stability:
            # Pre-compute once, fast run over threshold range (incl. 0.6 for r_ml)
            import numpy as np
            import statistics
            thresholds = np.arange(
                args.stability_start,
                args.stability_end + args.stability_step / 2,
                args.stability_step,
            ).tolist()
            thresholds = [round(t, 2) for t in thresholds]
            if 0.6 not in thresholds:
                thresholds = sorted(set(thresholds + [0.6]))
            print(f"\n--- Threshold Stability ({len(thresholds)} thresholds: {args.stability_start:.2f}-{args.stability_end:.2f}) ---")
            print("Pre-compute once -> fast run over all thresholds")
            print()
            df_stability, r_ml, st_cache = engine_ml.run_stability(
                period=args.period, thresholds=thresholds, primary_threshold=0.6
            )
            print(df_stability.to_string(index=False))
            print()
            if r_ml is None:
                r_ml = engine_ml.run(period=args.period)
            _print_result("Stat + ML (0.60)", r_ml)
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
            # Error Type Analysis (reuses cache from stability — no extra precompute)
            dec, rets, ref = st_cache
            err = engine_ml.error_type_analysis(
                period=args.period, ml_threshold=0.6,
                decisions=dec, next_returns=rets, refit_every=ref,
            )
            print()
            print("--- Error Type (Stat Long, ML blocked @ 0.60) ---")
            print(f"  Saved Losses (ML blocked, price fell):      {err['saved_losses']}")
            print(f"  Missed Opportunities (ML blocked, price rose): {err['missed_opportunities']}")
        else:
            r_ml = engine_ml.run(period=args.period)
            _print_result("Stat + ML (0.60)", r_ml)

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

    print("\n" + "=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
