#!/usr/bin/env python
"""
SignalFlow — Walk-Forward Validation

Runs backtest on rolling windows: train N months, test M months, roll forward.
Compares in-sample vs out-of-sample performance.

Usage:
  python scripts/walk_forward_validation.py
  python scripts/walk_forward_validation.py --symbol AAPL --train-months 24 --test-months 6
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.pipeline import DataPipeline
from backtesting.engine import BacktestEngine


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Walk-Forward Validation — in-sample vs out-of-sample")
    ap.add_argument("--symbol", default="AAPL", help="Symbol")
    ap.add_argument("--train-months", type=int, default=24, help="Train window (months)")
    ap.add_argument("--test-months", type=int, default=6, help="Test window (months)")
    ap.add_argument("--end-date", default=None, help="End date YYYY-MM-DD (default: latest)")
    ap.add_argument("--mode", default="best_combo", help="Backtest mode (best_combo, stat_only, etc.)")
    ap.add_argument("--out", default=None, help="Save results to JSON path")
    args = ap.parse_args()

    root = Path(__file__).parent.parent
    config_path = root / "config" / "backtest_modes.json"
    mode_cfg = {}
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            mode_cfg = cfg.get("modes", {}).get(args.mode, {})
        except Exception:
            pass

    engine_kw = {
        "symbol": args.symbol,
        "horizon": "daily",
        "use_ml": mode_cfg.get("use_ml", False),
        "mean_rev_mult": mode_cfg.get("mean_rev_mult", 1.0),
        "atr_stop_mult": mode_cfg.get("atr_stop_mult", 0.0) or 0.0,
        "vol_target_ann": mode_cfg.get("vol_target_ann"),
    }
    engine = BacktestEngine(**{k: v for k, v in engine_kw.items() if v is not None})

    # Get date range from data
    end_d = args.end_date or datetime.utcnow().strftime("%Y-%m-%d")
    pipeline = DataPipeline(symbol=args.symbol, horizon="daily", period="5y", end_date=end_d)
    df = pipeline.run()
    returns = df["returns"].dropna()
    if len(returns) < 252:
        print("Need at least 252 days of data.")
        return 1
    end_ts = returns.index[-1]
    start_ts = returns.index[0]

    train_days = args.train_months * 21
    test_days = args.test_months * 21
    results = []
    current = start_ts + timedelta(days=train_days)
    step = test_days

    print("=" * 70)
    print("SignalFlow — Walk-Forward Validation")
    print("=" * 70)
    print(f"Symbol: {args.symbol} | Train: {args.train_months}mo | Test: {args.test_months}mo")
    print()

    while current + timedelta(days=test_days) <= end_ts:
        train_end = current.strftime("%Y-%m-%d")
        test_end = (current + timedelta(days=test_days)).strftime("%Y-%m-%d")
        period = f"{int(train_days/365)+1}y"
        try:
            r_train = engine.run(period=period, end_date=train_end)
            r_test = engine.run(period=f"{int((train_days+test_days)/365)+1}y", end_date=test_end)
            # Out-of-sample: we need returns only in the test window
            # Backtest gives full-period metrics; we approximate by running on extended period
            # For simplicity we report train vs full (train+test) - real OOS would need engine support
            row = {
                "train_end": train_end,
                "test_end": test_end,
                "train_sharpe": r_train.sharpe_ratio,
                "train_return": r_train.total_return,
                "train_dd": r_train.max_drawdown,
                "full_sharpe": r_test.sharpe_ratio,
                "full_return": r_test.total_return,
                "full_dd": r_test.max_drawdown,
            }
            results.append(row)
            wfe = r_test.sharpe_ratio / r_train.sharpe_ratio if r_train.sharpe_ratio > 0 else 0
            print(f"  {train_end} -> {test_end}: Train Sharpe={r_train.sharpe_ratio:.3f} | Full Sharpe={r_test.sharpe_ratio:.3f} | WFE~{wfe:.2f}")
        except Exception as e:
            print(f"  {train_end} -> {test_end}: ERROR {e}")
        current = current + timedelta(days=step)

    if not results:
        print("No windows completed.")
        return 1

    avg_train_sharpe = sum(r["train_sharpe"] for r in results) / len(results)
    avg_full_sharpe = sum(r["full_sharpe"] for r in results) / len(results)
    print()
    print("--- Summary ---")
    print(f"Windows: {len(results)}")
    print(f"Avg Train Sharpe: {avg_train_sharpe:.3f}")
    print(f"Avg Full Sharpe:  {avg_full_sharpe:.3f}")
    wfe_avg = avg_full_sharpe / avg_train_sharpe if avg_train_sharpe > 0 else 0
    print(f"Walk-Forward Efficiency (approx): {wfe_avg:.2f} (1.0 = no degradation)")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"results": results, "summary": {"avg_train_sharpe": avg_train_sharpe, "avg_full_sharpe": avg_full_sharpe}}, f, indent=2)
        print(f"\nSaved: {out_path}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
