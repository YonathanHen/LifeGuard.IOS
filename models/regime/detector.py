"""
SignalFlow — Regime Detector
HMM on volatility + returns. Horizon-aware.
Regimes: Trend / Mean-Reverting / High-Volatility
"""
import numpy as np
import pandas as pd
import warnings
from typing import Tuple, Optional

try:
    from hmmlearn import hmm
    HAS_HMM = True
except ImportError:
    HAS_HMM = False


REGIME_LABELS = ["trend", "mean_reverting", "high_volatility"]


def _volatility_series(returns: pd.Series, window: int = 20) -> pd.Series:
    """Rolling annualized volatility."""
    return returns.rolling(window, min_periods=window // 2).std() * np.sqrt(252)


class RegimeDetector:
    """
    HMM-based regime detection on (returns, volatility).
    Horizon-aware: different interpretation per horizon.
    """

    def __init__(self, n_states: int = 3, horizon: str = "daily"):
        self.n_states = n_states
        self.horizon = horizon
        self._model = None
        self._state_labels = None  # maps state index to regime name

    def fit(self, returns: pd.Series) -> "RegimeDetector":
        """Fit HMM on (returns, volatility) features."""
        if not HAS_HMM:
            self._model = None
            return self

        vol = _volatility_series(returns).dropna()
        common = returns.index.intersection(vol.index)
        ret_aligned = returns.loc[common].dropna()
        vol_aligned = vol.loc[ret_aligned.index]

        X = np.column_stack([ret_aligned.values * 100, vol_aligned.values])  # scale returns for stability
        X = X[~np.any(np.isnan(X), axis=1)]

        if len(X) < 100:
            self._model = None
            return self

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                model = hmm.GaussianHMM(
                    n_components=self.n_states,
                    covariance_type="diag",
                    n_iter=200,
                    random_state=42,
                )
                model.fit(X)

            # Label states: by volatility (ascending) -> trend, mean_reverting, high_vol
            means = model.means_
            vol_means = means[:, 1]  # second column is volatility
            state_order = np.argsort(vol_means)
            self._model = model
            self._state_labels = [REGIME_LABELS[i] for i in state_order]
        except Exception:
            self._model = None
            self._state_labels = None

        return self

    def predict(self, returns: pd.Series) -> Tuple[str, bool]:
        """
        Returns (regime_name, regime_stable).
        regime_stable=False when High-Volatility → suppress direction.
        """
        out = self.predict_with_proba(returns)
        return out[0], out[1]

    def predict_with_proba(self, returns: pd.Series) -> Tuple[str, bool, float]:
        """
        Returns (regime_name, regime_stable, max_prob).
        max_prob used for Cooldown trigger (>80% for 2 consecutive days).
        """
        if not HAS_HMM or self._model is None:
            return "unknown", True, 0.0

        vol = _volatility_series(returns).dropna()
        common = returns.index.intersection(vol.index)
        if len(common) < 5:
            return "unknown", True, 0.0

        ret_recent = returns.loc[common].tail(50).values * 100
        vol_recent = vol.loc[common].tail(50).values
        X = np.column_stack([ret_recent, vol_recent])

        try:
            # predict_proba: (n_samples, n_states) — use last row for current state
            posteriors = self._model.predict_proba(X)
            last_probs = posteriors[-1]
            max_prob = float(np.max(last_probs))
            current_state = int(np.argmax(last_probs))
            regime = self._state_labels[current_state]
            regime_stable = regime != "high_volatility"
            return regime, regime_stable, max_prob
        except Exception:
            return "unknown", True, 0.0
