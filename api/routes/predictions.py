"""
SignalFlow — Prediction endpoint
GET /predict/{symbol}?horizon=daily
"""
import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException, Query
from typing import Literal, Optional

from data.pipeline import DataPipeline
from models.regime import RegimeDetector
from models.ml.lstm_model import LSTMPredictor
from models.ml.ensemble import ensemble_decision
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import (
    has_statistical_edge,
    liquidity_gate,
    confidence_factors,
    overall_confidence,
    system_assessment,
)
from models.rules.cross_asset import check_cross_asset_alignment
from models.rules.cooldown import check_cooldown

router = APIRouter()


def _vol_bucket_to_risk(bucket: str) -> int:
    """Map volatility bucket to risk score 0-100."""
    return {"low": 25, "medium": 50, "high": 75}.get(bucket, 50)


def _default_ml_threshold() -> float:
    """ML threshold from env (calibrated) or 0.6."""
    return float(os.environ.get("ML_THRESHOLD", "0.6"))


@router.get("/{symbol}")
def predict(
    symbol: str,
    horizon: Literal["daily", "weekly", "regime_outlook"] = Query("daily"),
    ml_threshold: Optional[float] = Query(default=None, ge=0.5, le=0.9),
):
    """
    Get prediction for symbol.
    Context: { symbol, horizon } — First-Class Citizen.
    """
    if ml_threshold is None:
        ml_threshold = _default_ml_threshold()
    try:
        # Data
        pipeline = DataPipeline(symbol=symbol.upper(), horizon=horizon)
        df = pipeline.run()
        returns = df["returns"]
        data_stable = df["_stable"].iloc[-1] if "_stable" in df.columns else True

        # Regime (before Stat)
        regime_detector = RegimeDetector(horizon=horizon).fit(returns)
        regime_name, regime_stable, regime_max_prob = regime_detector.predict_with_proba(returns)
        prediction_date = returns.index[-1] if len(returns) > 0 else None

        # Cooldown state (updated after regime predict; applied after has_edge)
        in_cooldown = False
        cooldown_day = None
        cooldown_total = None
        if prediction_date is not None:
            in_cooldown, cooldown_day, cooldown_total = check_cooldown(
                symbol.upper(), horizon, prediction_date, regime_name, regime_max_prob
            )

        # Stat Core
        arima = ARIMAModel().fit(returns)
        arima_out = arima.predict_next()

        garch = GARCHModel().fit(returns)
        garch_out = garch.predict_next(horizon=horizon)

        # Rule Engine
        has_edge = has_statistical_edge(arima_out, garch_out)
        cross_asset_ok, cross_asset_reason = check_cross_asset_alignment(horizon=horizon)
        liq_ok = liquidity_gate(pipeline.get_dollar_volume_20d_avg())
        if not liq_ok:
            has_edge = False
        if not regime_stable:
            has_edge = False
        if in_cooldown:
            has_edge = False

        factors = confidence_factors(
            arima_out, garch_out, cross_asset_ok, liq_ok, regime_stable, bool(data_stable),
            cooldown_ok=not in_cooldown,
        )
        conf = overall_confidence(factors)
        assessment = (
            f"Cooling down: Day {cooldown_day}/{cooldown_total} — no decisions after regime shift."
            if in_cooldown and cooldown_day and cooldown_total
            else system_assessment(has_edge, conf, garch_out["volatility_bucket"])
        )

        risk_score = _vol_bucket_to_risk(garch_out["volatility_bucket"])

        # ML Layer (Phase 2B) — daily only (helps daily, hurts weekly)
        ml_probs = None
        lstm = LSTMPredictor()
        if horizon == "daily" and lstm.load():
            ml_probs = lstm.predict_proba(df)
            if ml_probs is not None:
                should_trade, _ = ensemble_decision(
                    has_edge, arima_out["direction"], ml_probs, threshold=ml_threshold
                )
                if not should_trade:
                    has_edge = False

        resp = {
            "symbol": symbol.upper(),
            "horizon": horizon,
            "direction": arima_out["direction"],
            "magnitude": arima_out["magnitude"],
            "volatility_bucket": garch_out["volatility_bucket"],
            "risk_score": risk_score,
            "has_edge": has_edge,
            "confidence": conf,
            "ml_probs": ml_probs,
            "ml_available": lstm.is_available(),
            "system_assessment": assessment,
            "confidence_factors": factors,
            "cross_asset_reason": cross_asset_reason,
            "regime": regime_name,
            "external_features_available": pipeline.is_fred_available(),
        }
        if in_cooldown and cooldown_day is not None and cooldown_total is not None:
            resp["cooldown"] = True
            resp["cooldown_day"] = cooldown_day
            resp["cooldown_total"] = cooldown_total
        else:
            resp["cooldown"] = False
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
