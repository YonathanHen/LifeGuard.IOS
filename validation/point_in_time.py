"""
SignalFlow — Point-in-Time Validation
בודק תחזיות על היסטוריה: לוקח תאריכים רנדומליים, מריץ חיזוי עם מידע עד לאותו תאריך,
ובודק מול התוצאה האמיתית.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import random
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

from data.pipeline import DataPipeline
from data.fetchers.yahoo_finance import fetch_yahoo, resample_to_horizon
from data.fetchers.cross_asset import fetch_cross_asset
from models.regime import RegimeDetector
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import (
    has_statistical_edge,
    liquidity_gate,
    confidence_factors,
    overall_confidence,
    system_assessment,
)
from models.rules.cross_asset import check_cross_asset_alignment_from_series


def _vol_bucket_to_risk(bucket: str) -> int:
    return {"low": 25, "medium": 50, "high": 75}.get(bucket, 50)


def run_point_in_time_prediction(
    symbol: str,
    horizon: str,
    as_of_date: str,
    skip_cooldown: bool = True,
) -> Tuple[Optional[Dict[str, Any]], Optional[float], Optional[str]]:
    """
    הרצת חיזוי בנקודת זמן מסוימת — משתמש רק במידע עד as_of_date.
    Returns (prediction_dict, actual_next_return, error_msg).
    actual_next_return = התשואה בפועל של התקופה הבאה (יומי/שבועי/חודשי).
    """
    try:
        pipeline = DataPipeline(
            symbol=symbol.upper(),
            horizon=horizon,
            period="2y",
            end_date=as_of_date,
        )
        df = pipeline.run()
        returns = df["returns"]
        min_len = {"daily": 252, "weekly": 52, "regime_outlook": 12}.get(horizon, 252)
        if len(returns) < min_len:
            return None, None, f"Insufficient data: {len(returns)} observations"
        data_stable = df["_stable"].iloc[-1] if "_stable" in df.columns else True

        # Regime
        regime_detector = RegimeDetector(horizon=horizon).fit(returns)
        regime_name, regime_stable, regime_max_prob = regime_detector.predict_with_proba(returns)

        # Cooldown — בדיקת validation: מדלגים על cooldown (אין state היסטורי)
        in_cooldown = False
        if not skip_cooldown:
            from models.rules.cooldown import check_cooldown
            pred_dt = returns.index[-1]
            in_cooldown, _, _ = check_cooldown(
                symbol.upper(), horizon, pred_dt, regime_name, regime_max_prob
            )

        # Cross-Asset — point-in-time
        end_d = pd.Timestamp(as_of_date) + pd.Timedelta(days=1)
        start_d = end_d - pd.Timedelta(days=180)
        sp, vix = fetch_cross_asset(
            horizon=horizon,
            start_date=start_d.strftime("%Y-%m-%d"),
            end_date=end_d.strftime("%Y-%m-%d"),
        )
        cross_ok, cross_reason = check_cross_asset_alignment_from_series(sp, vix)

        # Stat Core
        arima = ARIMAModel().fit(returns)
        arima_out = arima.predict_next()
        garch = GARCHModel().fit(returns)
        garch_out = garch.predict_next(horizon=horizon)

        has_edge = has_statistical_edge(arima_out, garch_out)
        liq_ok = liquidity_gate(pipeline.get_dollar_volume_20d_avg())
        if not liq_ok:
            has_edge = False
        if not regime_stable:
            has_edge = False
        if in_cooldown:
            has_edge = False

        factors = confidence_factors(
            arima_out, garch_out, cross_ok, liq_ok, regime_stable, bool(data_stable),
            cooldown_ok=not in_cooldown,
        )
        conf = overall_confidence(factors)
        assessment = system_assessment(has_edge, conf, garch_out["volatility_bucket"])
        risk_score = _vol_bucket_to_risk(garch_out["volatility_bucket"])

        pred = {
            "symbol": symbol.upper(),
            "horizon": horizon,
            "direction": arima_out["direction"],
            "magnitude": arima_out["magnitude"],
            "volatility_bucket": garch_out["volatility_bucket"],
            "risk_score": risk_score,
            "has_edge": has_edge,
            "confidence": conf,
            "system_assessment": assessment,
            "regime": regime_name,
        }

        # Actual next return — נדרש fetch נוסף קטן
        actual_ret = _get_actual_next_return(symbol, horizon, as_of_date)
        if actual_ret is None:
            return pred, None, "Could not fetch actual next return"

        return pred, actual_ret, None
    except Exception as e:
        return None, None, str(e)


def _get_actual_next_return(symbol: str, horizon: str, as_of_date: str) -> Optional[float]:
    """מחזיר את התשואה בפועל של התקופה הבאה."""
    as_of = pd.Timestamp(as_of_date).normalize()
    buffer = 35 if horizon == "daily" else (50 if horizon == "weekly" else 45)
    start_offset = 2 if horizon == "daily" else 14  # weekly/monthly need prior period
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
        # Align timezone for comparison (yfinance may return tz-aware)
        if prices.index.tz is not None:
            as_of = as_of.tz_localize(prices.index.tz, ambiguous=True)
        if horizon == "daily":
            # Next day return: close at as_of -> close at next trading day
            after = prices.index[prices.index > as_of]
            before_or_eq = prices.index[prices.index <= as_of]
            if len(after) == 0 or len(before_or_eq) == 0:
                return None
            next_date = after[0]
            price_as_of = prices.loc[before_or_eq[-1]]
            price_next = prices.loc[next_date]
            return float((price_next - price_as_of) / price_as_of)
        if horizon == "weekly":
            raw_w = resample_to_horizon(raw, "weekly")
            raw_w.index = raw_w.index.normalize()
            pw = raw_w[close_col].dropna()
            after = pw.index[pw.index > as_of]
            before_or_eq = pw.index[pw.index <= as_of]
            if len(after) == 0 or len(before_or_eq) == 0:
                return None
            next_week = after[0]
            price_as_of = pw.loc[before_or_eq[-1]]
            price_next = pw.loc[next_week]
            return float((price_next - price_as_of) / price_as_of)
        # regime_outlook — monthly
        raw_m = raw.resample("ME").last().dropna()
        raw_m.index = raw_m.index.normalize()
        pm = raw_m[close_col]
        after = pm.index[pm.index > as_of]
        before_or_eq = pm.index[pm.index <= as_of]
        if len(after) == 0 or len(before_or_eq) == 0:
            return None
        next_month = after[0]
        price_as_of = pm.loc[before_or_eq[-1]]
        price_next = pm.loc[next_month]
        return float((price_next - price_as_of) / price_as_of)
    except Exception:
        return None


def _is_correct(pred_direction: str, actual_return: float) -> Optional[bool]:
    """
    האם החיזוי היה נכון?
    up + actual>0 = True, down + actual<0 = True, flat = None (לא בודקים)
    """
    if pred_direction == "flat":
        return None
    if pred_direction == "up":
        return actual_return > 0
    if pred_direction == "down":
        return actual_return < 0
    return None


@dataclass
class ValidationResult:
    horizon: str
    total: int
    correct: int
    incorrect: int
    skipped_flat: int
    samples: list


def run_validation(
    symbol: str = "AAPL",
    samples_per_horizon: int = 15,
    seed: Optional[int] = None,
) -> Dict[str, ValidationResult]:
    """
    הרצת אימות: 15 samples לכל horizon (daily, weekly, regime_outlook).
    תאריכים רנדומליים מהעבר, ללא מידע עתידי.
    """
    if seed is not None:
        random.seed(seed)

    # Fetch full history to get valid date range
    full = fetch_yahoo(symbol, period="5y")
    if full.empty or len(full) < 400:
        raise ValueError(f"Insufficient history for {symbol}")

    dates = full.index
    min_date = dates[252]  # שנה מינימלית להכשרה
    max_date = dates[-1] - pd.Timedelta(days=40)  # buffer לתשואה הבאה (חייב להיות בעבר)

    valid_dates = [d for d in dates if min_date <= d <= max_date]
    if len(valid_dates) < samples_per_horizon * 3:
        raise ValueError(f"Not enough valid dates: {len(valid_dates)}")

    horizons = ["daily", "weekly", "regime_outlook"]
    results = {}

    for horizon in horizons:
        selected = random.sample(valid_dates, min(samples_per_horizon, len(valid_dates)))
        correct = 0
        incorrect = 0
        skipped = 0
        sample_details = []

        for as_of_dt in selected:
            as_of_str = as_of_dt.strftime("%Y-%m-%d") if hasattr(as_of_dt, "strftime") else str(as_of_dt)[:10]
            pred, actual_ret, err = run_point_in_time_prediction(symbol, horizon, as_of_str)
            if err:
                sample_details.append({"date": as_of_str, "error": err})
                continue
            if actual_ret is None:
                sample_details.append({"date": as_of_str, "error": "No actual return"})
                continue

            direction = pred.get("direction", "flat")
            verdict = _is_correct(direction, actual_ret)
            if verdict is None:
                skipped += 1
                sample_details.append({
                    "date": as_of_str,
                    "direction": direction,
                    "actual_ret": round(actual_ret * 100, 2),
                    "result": "skipped (flat)",
                })
            else:
                if verdict:
                    correct += 1
                    sample_details.append({
                        "date": as_of_str,
                        "direction": direction,
                        "actual_ret": round(actual_ret * 100, 2),
                        "result": "correct",
                    })
                else:
                    incorrect += 1
                    sample_details.append({
                        "date": as_of_str,
                        "direction": direction,
                        "actual_ret": round(actual_ret * 100, 2),
                        "result": "incorrect",
                    })

        results[horizon] = ValidationResult(
            horizon=horizon,
            total=correct + incorrect,
            correct=correct,
            incorrect=incorrect,
            skipped_flat=skipped,
            samples=sample_details,
        )

    return results
