"""
SignalFlow — Strategy-Based Backtesting
Metrics: Sharpe, Max Drawdown, Hit rate, Exposure, Regime breakdown.
Uses Regime, Cross-Asset, Liquidity. Optional: ML layer, costs.
"""
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict

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
    hit_rate: float
    equity_curve: pd.Series
    exposure_pct: float = 0.0  # Time in market (% of days)
    n_days: int = 0
    by_regime: Optional[Dict[str, "BacktestResult"]] = None


def _precompute_ml_probs(
    symbol: str,
    horizon: str,
    dates: pd.DatetimeIndex,
    lookback: int = 40,
) -> Dict[pd.Timestamp, Optional[Dict[str, float]]]:
    """
    Pre-compute LSTM predict_proba for each date (point-in-time).
    Returns dict: date -> {P_up, P_down, P_flat} or None.
    """
    try:
        from models.ml.lstm_model import LSTMPredictor
    except ImportError:
        return {d: None for d in dates}

    lstm = LSTMPredictor(lookback=lookback)
    if not lstm.load():
        return {d: None for d in dates}

    cache = {}
    for dt in dates:
        try:
            pipeline = DataPipeline(
                symbol=symbol,
                horizon=horizon,
                period="2y",
                end_date=dt.strftime("%Y-%m-%d"),
            )
            df = pipeline.run()
            if len(df) >= lookback + 1:
                probs = lstm.predict_proba(df)
                cache[dt] = probs
            else:
                cache[dt] = None
        except Exception:
            cache[dt] = None
    return cache


class BacktestEngine:
    """
    Walk-forward backtest: refit ARIMA+GARCH periodically, simulate positions.
    Position: Long when has_edge + direction=up, Flat otherwise.
    With use_ml=True: also requires ML ensemble approval (Stat AND ML).
    """

    def __init__(
        self,
        symbol: str = "AAPL",
        horizon: str = "daily",
        refit_every: int = 5,
        train_min_days: int = 252,
        use_ml: bool = False,
        ml_threshold: float = 0.6,
        commission_bps: float = 5.0,
        slippage_bps: float = 3.0,
    ):
        self.symbol = symbol
        self.horizon = horizon
        self.refit_every = refit_every
        self.train_min_days = train_min_days
        self.use_ml = use_ml and horizon == "daily"
        self.ml_threshold = ml_threshold
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps

    def run(self, period: str = "3y") -> BacktestResult:
        """Run backtest, return metrics."""
        pipeline = DataPipeline(self.symbol, self.horizon, period=period)
        df = pipeline.run()
        returns = df["returns"].dropna()

        if len(returns) < self.train_min_days + 50:
            raise ValueError(f"Need at least {self.train_min_days + 50} days, got {len(returns)}")

        start_dt = returns.index[0]
        end_dt = returns.index[-1]
        sp, vix = fetch_cross_asset(
            horizon=self.horizon,
            start_date=start_dt.strftime("%Y-%m-%d"),
            end_date=end_dt.strftime("%Y-%m-%d"),
        )

        if "dollar_volume_20d" in df.columns:
            dv_aligned = df["dollar_volume_20d"].reindex(returns.index).ffill()
        else:
            dv_aligned = None

        # Pre-compute ML probs if use_ml
        ml_cache = {}
        if self.use_ml:
            backtest_dates = returns.index[self.train_min_days : len(returns) - 1]
            ml_cache = _precompute_ml_probs(
                self.symbol, self.horizon, backtest_dates
            )

        round_trip_cost = 2 * (self.commission_bps + self.slippage_bps) / 10_000

        positions: List[int] = []
        realized_returns: List[float] = []
        regimes: List[str] = []

        for i in range(self.train_min_days, len(returns) - 1):
            if (i - self.train_min_days) % self.refit_every != 0 and len(positions) > 0:
                pos = positions[-1]
                regime_name = regimes[-1] if regimes else "unknown"
            else:
                train = returns.iloc[:i]
                dt_i = returns.index[i]
                try:
                    arima = ARIMAModel(order=(2, 0, 2)).fit(train)
                    garch = GARCHModel().fit(train)
                    arima_out = arima.predict_next()
                    garch_out = garch.predict_next()
                    has_edge = has_statistical_edge(arima_out, garch_out)

                    regime_detector = RegimeDetector(horizon=self.horizon).fit(train)
                    regime_name, regime_stable = regime_detector.predict(train)
                    if not regime_stable:
                        has_edge = False

                    sp_slice = sp.loc[sp.index <= dt_i].tail(30)
                    vix_slice = vix.loc[vix.index <= dt_i].tail(30)
                    cross_ok, _ = check_cross_asset_alignment_from_series(sp_slice, vix_slice)
                    if not cross_ok:
                        has_edge = False

                    dv = float(dv_aligned.iloc[i]) if dv_aligned is not None else 0.0
                    if not liquidity_gate(dv):
                        has_edge = False

                    if self.use_ml and has_edge and arima_out["direction"] == "up":
                        from models.ml.ensemble import ensemble_decision
                        ml_probs = ml_cache.get(dt_i) if dt_i in ml_cache else None
                        has_ens, _ = ensemble_decision(
                            has_edge, arima_out["direction"], ml_probs, self.ml_threshold
                        )
                        has_edge = has_ens

                    pos = 1 if has_edge and arima_out["direction"] == "up" else 0
                except Exception:
                    pos = 0
                    regime_name = "unknown"

            positions.append(pos)
            regimes.append(regime_name)

            ret = pos * returns.iloc[i + 1]
            if round_trip_cost > 0 and pos == 1 and (len(positions) == 1 or positions[-2] == 0):
                ret -= round_trip_cost
            realized_returns.append(ret)

        strat_returns = pd.Series(realized_returns)

        sharpe = self._sharpe(strat_returns)
        dd = self._max_drawdown(strat_returns)
        total_ret = float((1 + strat_returns).prod() - 1)
        equity = (1 + strat_returns).cumprod()

        long_days = [j for j, p in enumerate(positions) if p == 1]
        hit_rate = 0.0
        if long_days:
            hits = sum(1 for j in long_days if realized_returns[j] > 0)
            hit_rate = hits / len(long_days)

        exposure_pct = 100.0 * sum(positions) / len(positions) if positions else 0.0

        # Regime breakdown (optional)
        by_regime = None
        if regimes:
            regime_to_indices: Dict[str, List[int]] = {}
            for j, r in enumerate(regimes):
                regime_to_indices.setdefault(r, []).append(j)
            by_regime = {}
            for rname, indices in regime_to_indices.items():
                if len(indices) < 10:
                    continue
                sub_ret = strat_returns.iloc[indices]
                sub_pos = [positions[j] for j in indices]
                sub_long = [j for j in indices if positions[j] == 1]
                sub_hits = sum(1 for j in sub_long if realized_returns[j] > 0) if sub_long else 0
                by_regime[rname] = BacktestResult(
                    sharpe_ratio=self._sharpe(sub_ret),
                    max_drawdown=self._max_drawdown(sub_ret),
                    total_return=float((1 + sub_ret).prod() - 1),
                    n_trades=sum(sub_pos),
                    hit_rate=sub_hits / len(sub_long) if sub_long else 0.0,
                    equity_curve=sub_ret,
                    exposure_pct=100.0 * sum(sub_pos) / len(sub_pos) if sub_pos else 0.0,
                    n_days=len(indices),
                )

        return BacktestResult(
            sharpe_ratio=sharpe,
            max_drawdown=dd,
            total_return=total_ret,
            n_trades=sum(positions),
            hit_rate=hit_rate,
            equity_curve=equity,
            exposure_pct=exposure_pct,
            n_days=len(positions),
            by_regime=by_regime,
        )

    def _sharpe(self, returns: pd.Series, risk_free: float = 0.0) -> float:
        if returns.empty or returns.std() == 0:
            return 0.0
        excess = returns.mean() - risk_free / 252
        return float(excess / returns.std() * np.sqrt(252))

    def _max_drawdown(self, returns: pd.Series) -> float:
        if returns.empty:
            return 0.0
        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        dd = (cum - running_max) / running_max
        return float(dd.min())
