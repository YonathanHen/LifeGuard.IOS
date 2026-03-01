"""
SignalFlow — ARIMA Model
Output: bucket (↑/→/↓) + magnitude (Low/Medium) — NOT exact number
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional
from statsmodels.tsa.arima.model import ARIMA

# Magnitude thresholds (bps) — adjustable
MAGNITUDE_LOW = 5   # 0.05%
MAGNITUDE_MED = 15  # 0.15%


def _return_to_bucket(mean_return: float) -> str:
    """Convert expected return to direction bucket."""
    if mean_return > 0.0005:   # 5 bps
        return "up"
    if mean_return < -0.0005:
        return "down"
    return "flat"


def _return_to_magnitude(abs_return_bps: float) -> str:
    """Convert to Low/Medium."""
    if abs_return_bps >= MAGNITUDE_MED:
        return "medium"
    if abs_return_bps >= MAGNITUDE_LOW:
        return "low"
    return "low"


class ARIMAModel:
    """
    ARIMA for direction expectation.
    Phase 1: bucket + magnitude, not exact number.
    """

    def __init__(self, order: Tuple[int, int, int] = (2, 0, 2)):
        self.order = order
        self._model = None

    def fit(self, returns: pd.Series) -> "ARIMAModel":
        """Fit ARIMA on returns."""
        self._model = ARIMA(returns, order=self.order).fit()
        return self

    def predict_next(self) -> dict:
        """
        One-step forecast. Returns bucket + magnitude.
        """
        if self._model is None:
            raise RuntimeError("Model not fitted")

        forecast = self._model.forecast(steps=1)
        mean_return = float(forecast.iloc[0])
        abs_bps = abs(mean_return) * 10_000

        return {
            "direction": _return_to_bucket(mean_return),
            "magnitude": _return_to_magnitude(abs_bps),
            "expected_return_bps": round(mean_return * 10_000, 2),  # for debugging
        }
