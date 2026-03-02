#!/usr/bin/env python
"""
SignalFlow — Calibrate ML Threshold (Phase 2B)
Grid search over threshold 0.52–0.70. Maximize Precision @ decisions.
Point-in-time; minimum 20 trades to avoid overfitting.
"""
import os
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import pandas as pd
from data.pipeline import DataPipeline
from data.fetchers.yahoo_finance import fetch_yahoo, resample_to_horizon
from data.fetchers.cross_asset import fetch_cross_asset
from models.ml.lstm_model import LSTMPredictor
from models.ml.ensemble import ensemble_decision
from models.regime import RegimeDetector
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import has_statistical_edge, liquidity_gate
from models.rules.cross_asset import check_cross_asset_alignment_from_series

MIN_TRADES_FOR_THRESHOLD = 20  # Avoid overfitting: need at least N decisions
THRESHOLDS = [0.52, 0.55, 0.58, 0.6, 0.62, 0.65, 0.68, 0.70]
LABEL_THRESH_BPS = 10  # 0.1% = up/down, else flat


def _get_actual_next_return(symbol: str, horizon: str, as_of_date: str) -> float | None:
    """Fetch actual next-period return (point-in-time)."""
    as_of = pd.Timestamp(as_of_date).normalize()
    buffer = 35 if horizon == "daily" else 50
    start_offset = 2 if horizon == "daily" else 14
    end_d = as_of + pd.Timedelta(days=buffer)
    try:
        raw = fetch_yahoo(
            symbol,
            start_date=(as_of - pd.Timedelta(days=start_offset)).strftime("%Y-%m-%d"),
            end_date=(end_d + pd.Timedelta(days=2)).strftime("%Y-%m-%d"),
            min_rows=2,
        )
        if raw.empty or len(raw) < 2:
            return None
        raw.index = raw.index.normalize()
        close_col = "Adj Close" if "Adj Close" in raw.columns else "Close"
        prices = raw[close_col].dropna()
        if prices.index.tz is not None:
            as_of = as_of.tz_localize(prices.index.tz, ambiguous=True)
        after = prices.index[prices.index > as_of]
        before_or_eq = prices.index[prices.index <= as_of]
        if len(after) == 0 or len(before_or_eq) == 0:
            return None
        price_as_of = prices.loc[before_or_eq[-1]]
        price_next = prices.loc[after[0]]
        return float((price_next - price_as_of) / price_as_of)
    except Exception:
        return None


def _run_prediction(symbol: str, horizon: str, as_of_date: str) -> dict | None:
    """
    Point-in-time prediction. Returns dict with direction, has_edge, ml_probs, actual_ret.
    Uses check_cross_asset_alignment_from_series with point-in-time SP/VIX.
    """
    try:
        pipeline = DataPipeline(symbol=symbol, horizon=horizon, period="2y", end_date=as_of_date)
        df = pipeline.run()
        returns = df["returns"]
        if len(returns) < 252:
            return None

        # Cross-asset: point-in-time SP/VIX
        end_d = pd.Timestamp(as_of_date) + pd.Timedelta(days=1)
        start_d = end_d - pd.Timedelta(days=180)
        sp, vix = fetch_cross_asset(
            horizon=horizon,
            start_date=start_d.strftime("%Y-%m-%d"),
            end_date=end_d.strftime("%Y-%m-%d"),
        )
        cross_ok, _ = check_cross_asset_alignment_from_series(sp, vix)

        arima = ARIMAModel().fit(returns)
        arima_out = arima.predict_next()
        garch = GARCHModel().fit(returns)
        garch_out = garch.predict_next(horizon=horizon)

        has_edge = has_statistical_edge(arima_out, garch_out) and liquidity_gate(pipeline.get_dollar_volume_20d_avg())
        regime = RegimeDetector(horizon=horizon).fit(returns)
        _, regime_stable, _ = regime.predict_with_proba(returns)
        if not regime_stable or not cross_ok:
            has_edge = False

        lstm = LSTMPredictor()
        ml_probs = None
        if lstm.load() and len(df) >= 45:
            ml_probs = lstm.predict_proba(df)

        actual_ret = _get_actual_next_return(symbol, horizon, as_of_date)
        if actual_ret is None:
            return None

        return {
            "direction": arima_out["direction"],
            "has_edge": has_edge,
            "ml_probs": ml_probs,
            "actual_ret": actual_ret,
        }
    except Exception:
        return None


def main():
    symbol = os.environ.get("CALIB_SYMBOL", "AAPL")
    horizon = "daily"
    n_dates = 60
    min_trades = MIN_TRADES_FOR_THRESHOLD

    print("=" * 60)
    print("SignalFlow — ML Threshold Calibration (Point-in-Time)")
    print("=" * 60)
    print(f"Symbol: {symbol} | Horizon: {horizon} | n_dates: {n_dates}")
    print(f"Min trades for threshold selection: {min_trades}")
    print("=" * 60)

    lstm = LSTMPredictor()
    if not lstm.load():
        print("LSTM model not found. Run: python scripts/train_lstm.py")
        return 1

    # Sample dates from last 2 years (same logic as validation)
    random.seed(42)
    full = fetch_yahoo(symbol, period="5y")
    if full.empty or len(full) < 500:
        print("Insufficient history")
        return 1
    dates = list(full.index)
    max_date = dates[-1] - pd.Timedelta(days=45)
    min_date = dates[252] if len(dates) > 252 else dates[0]
    valid = [d for d in dates if min_date <= d <= max_date]
    if len(valid) < n_dates:
        print(f"Only {len(valid)} valid dates")
        return 1
    sample = random.sample(valid, n_dates)

    results = []
    for d in sample:
        as_of = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        out = _run_prediction(symbol, horizon, as_of)
        if out:
            results.append({"as_of": as_of, **out})

    if len(results) < 10:
        print("Too few valid predictions for calibration.")
        return 1

    print(f"\nValid predictions: {len(results)}")

    # Label: up/down for |ret| > 10 bps
    thresh_val = LABEL_THRESH_BPS / 10_000
    best_thresh = 0.6
    best_precision = 0.0
    best_correct = 0
    best_total = 0

    print("\nThreshold | Decisions | Correct | Precision")
    print("-" * 50)
    for th in THRESHOLDS:
        correct, total = 0, 0
        for r in results:
            if not r["has_edge"] or r["direction"] == "flat":
                continue
            has_ens, _ = ensemble_decision(
                r["has_edge"], r["direction"], r["ml_probs"], threshold=th
            )
            if not has_ens:
                continue
            total += 1
            pred_up = r["direction"] == "up"
            actual_up = r["actual_ret"] > thresh_val
            if pred_up == actual_up:
                correct += 1
        prec = correct / total if total > 0 else 0
        marker = " *" if total >= min_trades and prec > best_precision else ""
        print(f"  {th:.2f}    |    {total:3d}   |   {correct:3d}   |  {prec:.2%}{marker}")
        # Only consider threshold if we have enough trades (avoid overfitting)
        if total >= min_trades and prec > best_precision:
            best_precision = prec
            best_thresh = th
            best_correct = correct
            best_total = total

    print("-" * 50)
    if best_total >= min_trades:
        print(f"\nRecommended threshold: {best_thresh} (Precision {best_precision:.2%} @ {best_total} decisions)")
    else:
        print(f"\nNo threshold with >= {min_trades} decisions. Best so far: {best_thresh}")
        print("Consider increasing n_dates or lowering min_trades for exploration.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
