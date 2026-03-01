"""
SignalFlow — GARCH Model
Volatility expectation. For regime_outlook: Low/Medium/High bucket only.
"""
import pandas as pd
import numpy as np
from typing import Optional
from statsmodels.tsa.stattools import adfuller

# For GARCH we need arch package - add to requirements
# Using simplified volatility proxy for Phase 1 if arch not available

try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False


def _vol_to_bucket(vol_annual: float, recent_vol: Optional[float] = None) -> str:
    """
    Convert volatility to Low/Medium/High.
    Compared to recent history. If no recent_vol, use simple percentiles.
    """
    if recent_vol is None:
        recent_vol = 20.0  # typical market
    if vol_annual > recent_vol * 1.5:
        return "high"
    if vol_annual < recent_vol * 0.7:
        return "low"
    return "medium"


class GARCHModel:
    """
    GARCH for volatility expectation.
    Returns: volatility (float) + bucket (low/medium/high) for regime_outlook.
    """

    def __init__(self, p: int = 1, q: int = 1):
        self.p, self.q = p, q
        self._model = None
        self._recent_vol = None
        self._last_vol = None

    def fit(self, returns: pd.Series) -> "GARCHModel":
        """Fit GARCH on returns."""
        # Drop NaN
        returns = returns.dropna()
        if len(returns) < 30:
            raise ValueError("Need at least 30 observations for GARCH")

        if HAS_ARCH:
            self._model = arch_model(returns * 100, vol="Garch", p=self.p, q=self.q)
            self._model = self._model.fit(disp="off")
            self._recent_vol = returns.tail(60).std() * np.sqrt(252) * 100  # annualized %
        else:
            # Fallback: use rolling vol
            self._model = None
            self._recent_vol = returns.tail(60).std() * np.sqrt(252) * 100

        self._last_vol = returns.tail(20).std() * np.sqrt(252) * 100
        return self

    def predict_next(self, horizon: str = "daily") -> dict:
        """
        One-step volatility forecast.
        For regime_outlook: bucket only (Low/Med/High).
        """
        if self._recent_vol is None:
            raise RuntimeError("Model not fitted")

        if HAS_ARCH and self._model is not None:
            fcast = self._model.forecast(horizon=1)
            vol_annual = float(np.sqrt(fcast.variance.iloc[-1, 0]))  # already in %
        else:
            vol_annual = self._last_vol

        bucket = _vol_to_bucket(vol_annual, self._recent_vol)

        return {
            "volatility_annual_pct": round(vol_annual, 2),
            "volatility_bucket": bucket,
        }
