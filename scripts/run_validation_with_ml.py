#!/usr/bin/env python
"""
SignalFlow — Point-in-Time Validation with ML Layer
40 תאריכים אקראיים לכל horizon — השוואת Stat Core בלבד vs Stat + ML (Ensemble)
"""
import sys
import random
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

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
from models.regime import RegimeDetector
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import has_statistical_edge, liquidity_gate
from models.rules.cross_asset import check_cross_asset_alignment_from_series
from models.ml.lstm_model import LSTMPredictor
from models.ml.ensemble import ensemble_decision

HORIZONS = ["daily", "weekly", "regime_outlook"]
MIN_LEN = {"daily": 252, "weekly": 52, "regime_outlook": 40}
MIN_DATE_OFFSET = {"daily": 252, "weekly": 260, "regime_outlook": 1008}  # trading days


def _get_actual_next_return(symbol: str, horizon: str, as_of_date: str) -> float | None:
    as_of = pd.Timestamp(as_of_date).normalize()
    buffer = 35 if horizon == "daily" else (50 if horizon == "weekly" else 45)
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
        if horizon == "daily":
            after = prices.index[prices.index > as_of]
            before_or_eq = prices.index[prices.index <= as_of]
            if len(after) == 0 or len(before_or_eq) == 0:
                return None
            price_as_of = prices.loc[before_or_eq[-1]]
            price_next = prices.loc[after[0]]
            return float((price_next - price_as_of) / price_as_of)
        if horizon == "weekly":
            raw_w = resample_to_horizon(raw, "weekly")
            raw_w.index = raw_w.index.normalize()
            pw = raw_w[close_col].dropna()
            after = pw.index[pw.index > as_of]
            before_or_eq = pw.index[pw.index <= as_of]
            if len(after) == 0 or len(before_or_eq) == 0:
                return None
            price_as_of = pw.loc[before_or_eq[-1]]
            price_next = pw.loc[after[0]]
            return float((price_next - price_as_of) / price_as_of)
        raw_m = raw.resample("ME").last().dropna()
        raw_m.index = raw_m.index.normalize()
        pm = raw_m[close_col]
        after = pm.index[pm.index > as_of]
        before_or_eq = pm.index[pm.index <= as_of]
        if len(after) == 0 or len(before_or_eq) == 0:
            return None
        price_as_of = pm.loc[before_or_eq[-1]]
        price_next = pm.loc[after[0]]
        return float((price_next - price_as_of) / price_as_of)
    except Exception:
        return None


def run_one(symbol: str, horizon: str, as_of_date: str, ml_threshold: float = 0.6) -> dict | None:
    try:
        period = "4y" if horizon == "regime_outlook" else "2y"
        pipeline = DataPipeline(symbol=symbol, horizon=horizon, period=period, end_date=as_of_date)
        df = pipeline.run()
        returns = df["returns"]
        if len(returns) < MIN_LEN.get(horizon, 252):
            return None

        regime = RegimeDetector(horizon=horizon).fit(returns)
        regime_name, regime_stable, regime_max_prob = regime.predict_with_proba(returns)

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

        has_edge_stat = has_statistical_edge(arima_out, garch_out)
        has_edge_stat = has_edge_stat and liquidity_gate(pipeline.get_dollar_volume_20d_avg())
        has_edge_stat = has_edge_stat and regime_stable and cross_ok

        ml_probs = None
        lstm = LSTMPredictor()
        if lstm.load() and len(df) >= 45:
            ml_probs = lstm.predict_proba(df)

        has_edge_ensemble, _ = ensemble_decision(
            has_edge_stat, arima_out["direction"], ml_probs, threshold=ml_threshold
        )

        actual_ret = _get_actual_next_return(symbol, horizon, as_of_date)
        if actual_ret is None:
            return None

        direction = arima_out["direction"]
        correct = None
        if direction != "flat":
            pred_up = direction == "up"
            actual_up = actual_ret > 0
            correct = pred_up == actual_up

        return {
            "horizon": horizon,
            "date": as_of_date,
            "direction": direction,
            "actual_ret_pct": round(actual_ret * 100, 2),
            "has_edge_stat": has_edge_stat,
            "has_edge_ensemble": has_edge_ensemble,
            "ml_probs": ml_probs,
            "correct": correct,
        }
    except Exception:
        return None


def _summary(results: list) -> tuple:
    stat_dec = [r for r in results if r["has_edge_stat"] and r["direction"] != "flat"]
    ens_dec = [r for r in results if r["has_edge_ensemble"] and r["direction"] != "flat"]
    stat_c = sum(1 for r in stat_dec if r["correct"])
    stat_t = len(stat_dec)
    ens_c = sum(1 for r in ens_dec if r["correct"])
    ens_t = len(ens_dec)
    return stat_t, stat_c, ens_t, ens_c


def main():
    symbol = "AAPL"
    n_per_horizon = 40
    seed = 42
    ml_threshold = 0.6

    random.seed(seed)
    print("=" * 65)
    print("SignalFlow — Point-in-Time Validation (Stat + ML)")
    print(f"40 dates per horizon | Symbol: {symbol} | ML threshold: {ml_threshold}")
    print("=" * 65)

    full = fetch_yahoo(symbol, period="5y")
    if full.empty or len(full) < 500:
        print("Insufficient history")
        return 1

    dates = list(full.index)
    max_date = dates[-1] - pd.Timedelta(days=45)
    all_results = []

    for horizon in HORIZONS:
        offset = MIN_DATE_OFFSET.get(horizon, 252)
        min_date = dates[offset] if len(dates) > offset else dates[0]
        valid = [d for d in dates if min_date <= d <= max_date]
        if len(valid) < n_per_horizon:
            print(f"  {horizon}: only {len(valid)} valid dates, need {n_per_horizon}")
            continue

        selected = random.sample(valid, n_per_horizon)
        results = []
        for d in selected:
            as_of = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
            r = run_one(symbol, horizon, as_of, ml_threshold)
            if r:
                results.append(r)

        stat_t, stat_c, ens_t, ens_c = _summary(results)
        stat_acc = stat_c / stat_t * 100 if stat_t > 0 else 0
        ens_acc = ens_c / ens_t * 100 if ens_t > 0 else 0

        print(f"\n--- {horizon.upper()} ({len(results)} valid) ---")
        print(f"  Stat Core only: {stat_t} decisions | {stat_c} correct | {stat_acc:.1f}%")
        print(f"  Stat + ML:      {ens_t} decisions | {ens_c} correct | {ens_acc:.1f}%")

        all_results.extend(results)

    if len(all_results) < 10:
        print("\nToo few valid results overall")
        return 1

    stat_t, stat_c, ens_t, ens_c = _summary(all_results)
    stat_acc = stat_c / stat_t * 100 if stat_t > 0 else 0
    ens_acc = ens_c / ens_t * 100 if ens_t > 0 else 0

    print("\n" + "=" * 65)
    print("--- TOTAL (all horizons) ---")
    print(f"  Stat Core only: {stat_t} decisions | {stat_c} correct | {stat_acc:.1f}%")
    print(f"  Stat + ML:      {ens_t} decisions | {ens_c} correct | {ens_acc:.1f}%")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
