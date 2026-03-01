#!/usr/bin/env python
"""
SignalFlow — Calibrate ML Threshold (Phase 2B)
Grid search over threshold 0.55–0.7. Maximize Precision @ decisions or Sharpe.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import pandas as pd
from data.pipeline import DataPipeline
from models.ml.lstm_model import LSTMPredictor
from models.ml.ensemble import ensemble_decision
from models.regime import RegimeDetector
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import has_statistical_edge, liquidity_gate
from models.rules.cross_asset import check_cross_asset_alignment


def _run_prediction(symbol: str, horizon: str, as_of_date: str) -> tuple:
    """Returns (direction, has_edge, ml_probs, actual_next_return) or None."""
    try:
        pipeline = DataPipeline(symbol=symbol, horizon=horizon, period="2y", end_date=as_of_date)
        df = pipeline.run()
        returns = df["returns"]
        if len(returns) < 252:
            return None
        arima = ARIMAModel().fit(returns)
        arima_out = arima.predict_next()
        garch = GARCHModel().fit(returns)
        garch_out = garch.predict_next(horizon=horizon)
        has_edge = has_statistical_edge(arima_out, garch_out) and liquidity_gate(pipeline.get_dollar_volume_20d_avg())
        regime = RegimeDetector(horizon=horizon).fit(returns)
        _, regime_stable, _ = regime.predict_with_proba(returns)
        if not regime_stable:
            has_edge = False
        cross_ok, _ = check_cross_asset_alignment(horizon=horizon)
        if not cross_ok:
            has_edge = False

        lstm = LSTMPredictor()
        ml_probs = None
        if lstm.load():
            ml_probs = lstm.predict_proba(df)

        next_ret = returns.shift(-1).iloc[-1] if len(returns) > 1 else None
        if pd.isna(next_ret):
            return None
        return (arima_out["direction"], has_edge, ml_probs, next_ret)
    except Exception:
        return None


def main():
    symbol = os.environ.get("CALIB_SYMBOL", "AAPL")
    horizon = "daily"
    n_dates = 30
    thresholds = [0.55, 0.58, 0.6, 0.62, 0.65, 0.7]

    print("=" * 55)
    print("SignalFlow — ML Threshold Calibration")
    print("=" * 55)
    print(f"Symbol: {symbol} | Horizon: {horizon} | n_dates: {n_dates}")

    lstm = LSTMPredictor()
    if not lstm.load():
        print("LSTM model not found. Run: python scripts/train_lstm.py")
        return 1

    # Random dates in last 2 years
    import random
    random.seed(42)
    end = pd.Timestamp.now()
    start = end - pd.Timedelta(days=730)
    dates = pd.date_range(start, end, freq="B")
    sample = random.sample(list(dates), min(n_dates, len(dates)))

    results = []
    for d in sample:
        as_of = d.strftime("%Y-%m-%d")
        out = _run_prediction(symbol, horizon, as_of)
        if out:
            direction, has_edge, ml_probs, actual_ret = out
            results.append({
                "as_of": as_of,
                "direction": direction,
                "has_edge": has_edge,
                "ml_probs": ml_probs,
                "actual_ret": actual_ret,
            })

    if len(results) < 5:
        print("Too few valid predictions for calibration.")
        return 1

    print(f"\nValid predictions: {len(results)}")

    best_thresh = 0.6
    best_precision = 0.0
    best_correct = 0
    best_total = 0

    print("\nThreshold | Decisions | Correct | Precision")
    print("-" * 45)
    for th in thresholds:
        correct, total = 0, 0
        for r in results:
            if not r["has_edge"]:
                continue
            if r["direction"] == "flat":
                continue
            st, _ = ensemble_decision(
                r["has_edge"], r["direction"], r["ml_probs"], threshold=th
            )
            if not st:
                continue
            total += 1
            pred_up = r["direction"] == "up"
            actual_up = r["actual_ret"] > 0.0005
            if pred_up == actual_up:
                correct += 1
        prec = correct / total if total > 0 else 0
        print(f"  {th:.2f}    |    {total:3d}   |   {correct:3d}   |  {prec:.2%}")
        if total >= 5 and prec > best_precision:
            best_precision = prec
            best_thresh = th
            best_correct = correct
            best_total = total

    print("-" * 45)
    print(f"\nRecommended threshold: {best_thresh} (Precision {best_precision:.2%} @ {best_total} decisions)")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
