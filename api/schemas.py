"""SignalFlow — API Schemas (Pydantic)."""
from typing import Literal, Optional
from pydantic import BaseModel


class PredictionResponse(BaseModel):
    symbol: str
    horizon: Literal["daily", "weekly", "regime_outlook"]

    direction: Literal["up", "down", "flat"]
    magnitude: Literal["low", "medium"]

    volatility_bucket: Literal["low", "medium", "high"]
    risk_score: int  # 0-100

    has_edge: bool
    confidence: Literal["low", "medium", "high"]
    system_assessment: str

    confidence_factors: list[tuple[str, bool]]
