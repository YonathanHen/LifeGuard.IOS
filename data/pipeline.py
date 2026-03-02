"""
SignalFlow — Data Pipeline
Orchestrates: Fetch → Resample → Preprocess → Features
"""
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from .fetchers import fetch_yahoo, fetch_cross_asset, fetch_macro_data
from .fetchers.yahoo_finance import resample_to_horizon
from .preprocessing import preprocess
from .features import compute_features

# Config
import sys
from pathlib import Path
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from config.settings import HORIZONS
except ImportError:
    HORIZONS = {
        "daily": {"z_score_window": 30},
        "weekly": {"z_score_window": 20},
        "regime_outlook": {"z_score_window": 12},
    }


class DataPipeline:
    """
    Data pipeline with horizon as First-Class Citizen.
    """

    def __init__(
        self,
        symbol: str,
        horizon: str = "daily",
        period: str = "5y",
        end_date: Optional[str] = None,
    ):
        self.symbol = symbol
        self.horizon = horizon
        self.period = period
        self.end_date = end_date  # Point-in-time: only data up to this date
        self._horizon_config = HORIZONS.get(horizon, HORIZONS["daily"])

    def run(self) -> pd.DataFrame:
        """Fetch, preprocess, features."""
        if self.end_date is not None:
            # Point-in-time: compute start from period (yfinance end is exclusive)
            end_d = pd.Timestamp(self.end_date)
            end_inclusive = (end_d + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            if "y" in self.period:
                years = int("".join(c for c in self.period if c.isdigit()) or 5)
                start_d = end_d - pd.Timedelta(days=365 * years)
            else:
                start_d = end_d - pd.Timedelta(days=365 * 2)
            # regime_outlook (monthly) needs 30+ obs for GARCH → 4y to be safe
            if self.horizon == "regime_outlook":
                start_d = end_d - pd.Timedelta(days=365 * 4)
            raw = fetch_yahoo(
                self.symbol,
                start_date=start_d.strftime("%Y-%m-%d"),
                end_date=end_inclusive,
            )
        else:
            raw = fetch_yahoo(self.symbol, period=self.period)
        raw = resample_to_horizon(raw, self.horizon)

        # Liquidity: dollar volume 20d avg (for Liquidity Gate)
        close_col = "Adj Close" if "Adj Close" in raw.columns else "Close"
        dollar_vol = (raw["Volume"] * raw[close_col]).dropna()
        dollar_vol_20d = dollar_vol.rolling(20, min_periods=1).mean()
        self._dollar_volume_20d_avg = float(dollar_vol.tail(20).mean()) if len(dollar_vol) >= 20 else 0.0

        # Preprocess
        z_window = self._horizon_config.get("z_score_window", 30)
        prep = preprocess(raw, horizon=self.horizon, z_window=z_window)

        # Features
        vol_window = 20 if self.horizon == "daily" else 12
        features = compute_features(
            prep["returns"],
            horizon=self.horizon,
            vol_window=vol_window,
        )
        features = features.join(prep[["_stable"]], how="inner")

        # Rolling dollar volume for backtest (point-in-time liquidity)
        dv_aligned = dollar_vol_20d.reindex(features.index).ffill()
        features["dollar_volume_20d"] = dv_aligned

        # External Features — VIX (Yahoo). For ML Layer.
        try:
            if self.end_date is not None:
                end_d = pd.Timestamp(self.end_date)
                end_inclusive = (end_d + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
                start_d = end_d - pd.Timedelta(days=365 * 5)
                _, vix = fetch_cross_asset(
                    horizon=self.horizon,
                    start_date=start_d.strftime("%Y-%m-%d"),
                    end_date=end_inclusive,
                )
            else:
                _, vix = fetch_cross_asset(horizon=self.horizon, period=self.period)
            if not vix.empty:
                if vix.index.tz is None and features.index.tz is not None:
                    vix = vix.copy()
                    vix.index = vix.index.tz_localize(features.index.tz)
                vix_aligned = vix.reindex(features.index).ffill()
                features["vix"] = vix_aligned
        except Exception:
            pass

        # External Features — FRED (Credit Spread + Yield Curve)
        # shift(1): ביום T המודל רואה נתוני T-1 — מניעת Look-ahead bias
        self._fred_available = False
        try:
            if self.end_date is not None:
                end_d = pd.Timestamp(self.end_date)
                start_d = end_d - pd.Timedelta(days=365 * 5)
                macro = fetch_macro_data(
                    start_date=start_d.strftime("%Y-%m-%d"),
                    end_date=(end_d + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                    series=["credit_spread", "yield_curve"],
                )
            else:
                macro = fetch_macro_data(period=self.period, series=["credit_spread", "yield_curve"])
            if not macro.empty:
                self._fred_available = True
                macro = macro.loc[~macro.index.duplicated(keep="last")]
                if macro.index.tz is None and features.index.tz is not None:
                    macro = macro.copy()
                    macro.index = macro.index.tz_localize(features.index.tz)
                elif macro.index.tz is not None and features.index.tz is None:
                    macro = macro.tz_localize(None)
                if self.horizon == "weekly":
                    macro = macro.resample("W").last().dropna()
                elif self.horizon == "regime_outlook":
                    macro = macro.resample("ME").last().dropna()
                for col in macro.columns:
                    aligned = macro[col].reindex(features.index).ffill()
                    aligned = aligned.shift(1)  # T sees T-1 — no look-ahead
                    features[col] = aligned
            else:
                pass
        except Exception:
            pass

        return features

    def get_dollar_volume_20d_avg(self) -> float:
        """Liquidity Gate — call after run()."""
        return getattr(self, "_dollar_volume_20d_avg", 0.0)

    def is_fred_available(self) -> bool:
        """External features (FRED) — for Fallback logic."""
        return getattr(self, "_fred_available", False)

    def get_returns_only(self) -> pd.Series:
        """For Stat Core — returns series only."""
        df = self.run()
        return df["returns"]
