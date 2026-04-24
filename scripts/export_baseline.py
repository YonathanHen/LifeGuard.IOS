#!/usr/bin/env python
"""
SignalFlow — Export Baseline Config
Creates/updates storage/baseline_config.json with current params for reproducibility.
Run before any algorithm changes to freeze state.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _git_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main():
    model_path = PROJECT / "storage" / "lstm_model.json"
    model_info = {}
    if model_path.exists():
        try:
            with open(model_path, encoding="utf-8") as f:
                model_info = json.load(f)
        except Exception:
            pass

    baseline = {
        "_comment": "Baseline configuration for full reproducibility.",
        "git_commit": _git_commit(),
        "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "algorithm": {
            "mode": "negative_filter",
            "disaster_threshold": float(
                os.environ.get("ML_NEGATIVE_FILTER_THRESHOLD")
                or os.environ.get("ML_DISASTER_THRESHOLD", "0.80")
            ),
            "ml_threshold": 0.6,
            "commission_bps": 5.0,
            "slippage_bps": 3.0,
            "train_min_days": 252,
            "refit_every": 1,
            "arima_order": [2, 0, 2],
        },
        "rules": {
            "liquidity_min_volume": 2_000_000,
            "cooldown_min_prob_trigger": 0.8,
        },
        "model": {
            "lookback": model_info.get("lookback", 40),
            "n_features": model_info.get("n_features", 4),
            "feature_cols": model_info.get("feature_cols", ["returns", "vix", "credit_spread", "yield_curve"]),
            "train_date": model_info.get("train_date", ""),
            "data_end_date": model_info.get("data_end_date", ""),
            "symbol": model_info.get("symbol", "AAPL"),
            "period": model_info.get("period", "5y"),
            "file": "storage/lstm_model.pt",
        },
        "files_to_preserve": [
            "storage/lstm_model.pt",
            "storage/lstm_model.json",
            "run_outputs/backtest_runs.json",
            "storage/backtest_runs.json",
            "storage/paper_decisions.json",
            "storage/paper_metrics.json",
        ],
        "reproduce": {
            "backtest": "python scripts/run_backtest_with_ml.py --period 5y --stability --disaster-threshold 0.80",
            "paper_daily": "python scripts/paper_trading_daily.py",
        },
    }

    out_path = PROJECT / "storage" / "baseline_config.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)

    print(f"Baseline saved: {out_path}")
    print(f"  Git: {baseline['git_commit']}")
    print(f"  Disaster threshold: {baseline['algorithm']['disaster_threshold']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
