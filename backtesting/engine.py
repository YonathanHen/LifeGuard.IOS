"""
SignalFlow — Strategy-Based Backtesting
Metrics: Sharpe, Max Drawdown, Hit rate (conditioned on risk)
Per PLANNING: Not accuracy — strategy performance.
Uses Regime, Cross-Asset, Liquidity (same logic as API).
"""
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.pipeline import DataPipeline
from data.fetchers.cross_asset import fetch_cross_asset
from models.regime import RegimeDetector
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import has_statistical_edge, liquidity_gate
from models.rules.cross_asset import check_cross_asset_alignment_from_series


@dataclass
class BacktestResult:
    """Backtest output — strategy metrics."""
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    n_trades: int
    hit_rate: float  # when we had edge and were right
    equity_curve: pd.Series


class BacktestEngine:
    """
    Walk-forward backtest: refit ARIMA+GARCH periodically, simulate positions.
    Position: Long when has_edge + direction=up, Flat otherwise.
    """

    def __init__(
        self,
        symbol: str = "AAPL",
        horizon: str = "daily",
        refit_every: int = 5,  # refit every N days (faster)
        train_min_days: int = 252,  # 1 year min for training
    ):
        self.symbol = symbol
        self.horizon = horizon
        self.refit_every = refit_every
        self.train_min_days = train_min_days

    def run(self, period: str = "3y") -> BacktestResult:
        """Run backtest, return metrics."""
        pipeline = DataPipeline(self.symbol, self.horizon, period=period)
        df = pipeline.run()
        returns = df["returns"].dropna()

        if len(returns) < self.train_min_days + 50:
            raise ValueError(f"Need at least {self.train_min_days + 50} days, got {len(returns)}")

        # Pre-fetch cross-asset for backtest (point-in-time)
        start_dt = returns.index[0]
        end_dt = returns.index[-1]
        sp, vix = fetch_cross_asset(
            horizon=self.horizon,
            start_date=start_dt.strftime("%Y-%m-%d"),
            end_date=end_dt.strftime("%Y-%m-%d"),
        )

        # dollar_volume_20d aligned to returns (for liquidity gate)
        if "dollar_volume_20d" in df.columns:
            dv_aligned = df["dollar_volume_20d"].reindex(returns.index).ffill()
        else:
            dv_aligned = None

        # Walk forward
        positions = []  # 1=long, 0=flat
        realized_returns = []

        for i in range(self.train_min_days, len(returns) - 1):
            if (i - self.train_min_days) % self.refit_every != 0 and len(positions) > 0:
                pos = positions[-1]
            else:
                train = returns.iloc[:i]
                dt_i = returns.index[i]
                try:
                    arima = ARIMAModel(order=(2, 0, 2)).fit(train)
                    garch = GARCHModel().fit(train)
                    arima_out = arima.predict_next()
                    garch_out = garch.predict_next()
                    has_edge = has_statistical_edge(arima_out, garch_out)

                    # Regime: suppress direction in high_vol
                    regime_detector = RegimeDetector(horizon=self.horizon).fit(train)
                    _, regime_stable = regime_detector.predict(train)
                    if not regime_stable:
                        has_edge = False

                    # Cross-Asset: conflict → no edge
                    sp_slice = sp.loc[sp.index <= dt_i].tail(30)
                    vix_slice = vix.loc[vix.index <= dt_i].tail(30)
                    cross_ok, _ = check_cross_asset_alignment_from_series(sp_slice, vix_slice)
                    if not cross_ok:
                        has_edge = False

                    # Liquidity gate
                    dv = float(dv_aligned.iloc[i]) if dv_aligned is not None else 0.0
                    if not liquidity_gate(dv):
                        has_edge = False

                    pos = 1 if has_edge and arima_out["direction"] == "up" else 0
                except Exception:
                    pos = 0

            positions.append(pos)
            realized_returns.append(pos * returns.iloc[i + 1])

        strat_returns = pd.Series(realized_returns)

        # Metrics
        sharpe = self._sharpe(strat_returns)
        dd = self._max_drawdown(strat_returns)
        total_ret = (1 + strat_returns).prod() - 1
        equity = (1 + strat_returns).cumprod()

        # Hit rate: when we were long, was next day positive?
        long_days = [i for i, p in enumerate(positions) if p == 1]
        if long_days:
            hits = sum(1 for j in long_days if realized_returns[j] > 0)
            hit_rate = hits / len(long_days)
        else:
            hit_rate = 0.0

        return BacktestResult(
            sharpe_ratio=sharpe,
            max_drawdown=dd,
            total_return=total_ret,
            n_trades=sum(positions),
            hit_rate=hit_rate,
            equity_curve=equity,
        )

    def _sharpe(self, returns: pd.Series, risk_free: float = 0.0) -> float:
        """Annualized Sharpe (252 trading days)."""
        if returns.std() == 0:
            return 0.0
        excess = returns.mean() - risk_free / 252
        return excess / returns.std() * np.sqrt(252)

    def _max_drawdown(self, returns: pd.Series) -> float:
        """Max drawdown from peak."""
        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        dd = (cum - running_max) / running_max
        return float(dd.min())
