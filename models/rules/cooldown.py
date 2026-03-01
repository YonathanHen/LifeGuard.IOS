"""
SignalFlow — Forced Cooldown after Regime Shift
Per PLANNING: Trigger when HMM >80% for new regime, 2 consecutive days.
During cooldown: No Edge.
"""
from datetime import datetime, timedelta
from typing import Tuple, Optional
from dataclasses import dataclass

try:
    from config.settings import load_horizons
    HORIZONS = load_horizons()
except Exception:
    HORIZONS = {"daily": {"cooldown_days": 3}, "weekly": {"cooldown_days": 7}}

# In-memory state: (symbol, horizon) -> CooldownState
_state: dict = {}


@dataclass
class CooldownState:
    last_regime: str
    last_date: Optional[datetime]
    streak: int  # consecutive days with same regime
    cooldown_until: Optional[datetime]
    cooldown_total: int


def _key(symbol: str, horizon: str) -> tuple:
    return (symbol.upper(), horizon)


def _cooldown_days(horizon: str) -> int:
    h = HORIZONS.get(horizon, HORIZONS.get("daily", {}))
    return int(h.get("cooldown_days", 3))


def check_cooldown(
    symbol: str,
    horizon: str,
    prediction_date: datetime,
    regime: str,
    max_prob: float,
    min_prob_trigger: float = 0.8,
) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Check and update cooldown state.
    Returns (in_cooldown, cooldown_day, cooldown_total).
    If in cooldown: cooldown_day=1..N, cooldown_total=N.
    """
    if horizon == "regime_outlook":
        return False, None, None

    key = _key(symbol, horizon)
    state = _state.get(key)
    cd_days = _cooldown_days(horizon)

    # Normalize prediction_date to date for comparison
    pred_d = prediction_date.date() if hasattr(prediction_date, "date") else prediction_date

    # Already in cooldown?
    if state and state.cooldown_until:
        until_d = state.cooldown_until.date() if hasattr(state.cooldown_until, "date") else state.cooldown_until
        if pred_d <= until_d:
            cooldown_start = state.cooldown_until - timedelta(days=cd_days)
            start_d = cooldown_start.date() if hasattr(cooldown_start, "date") else cooldown_start
            day_num = min(cd_days, max(1, (pred_d - start_d).days + 1))
            return True, day_num, cd_days

    # Cooldown ended — clear if we were in it
    if state and state.cooldown_until and pred_d > state.cooldown_until.date():
        state.cooldown_until = None
        state.streak = 0

    # Check for regime shift trigger: >80% for new regime, 2 consecutive days
    if regime == "unknown" or max_prob < min_prob_trigger:
        if state:
            state.streak = 0
        return False, None, None

    if state is None:
        _state[key] = CooldownState(
            last_regime=regime,
            last_date=prediction_date,
            streak=1,
            cooldown_until=None,
            cooldown_total=cd_days,
        )
        return False, None, None

    # Same regime as last time?
    if regime == state.last_regime:
        last_d = state.last_date.date() if state.last_date else None
        # New day (pred_d > last_d) = consecutive day of same regime
        if last_d and pred_d > last_d:
            state.streak += 1
        state.last_date = prediction_date
        if state.streak >= 2:
            state.cooldown_until = datetime.combine(
                pred_d, datetime.min.time()
            ) + timedelta(days=cd_days)
            return True, 1, cd_days
        return False, None, None

    # Regime changed — reset streak, new regime day 1
    state.last_regime = regime
    state.last_date = prediction_date
    state.streak = 1
    return False, None, None


def get_cooldown_status(
    symbol: str,
    horizon: str,
    prediction_date: datetime,
) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Check if currently in cooldown (without updating).
    Returns (in_cooldown, cooldown_day, cooldown_total).
    """
    if horizon == "regime_outlook":
        return False, None, None

    key = _key(symbol, horizon)
    state = _state.get(key)
    if not state or not state.cooldown_until:
        return False, None, None

    pred_d = prediction_date.date() if hasattr(prediction_date, "date") else prediction_date
    until_d = state.cooldown_until.date() if hasattr(state.cooldown_until, "date") else state.cooldown_until
    if pred_d > until_d:
        return False, None, None

    cd_days = _cooldown_days(horizon)
    cooldown_start = state.cooldown_until - timedelta(days=cd_days)
    start_d = cooldown_start.date() if hasattr(cooldown_start, "date") else cooldown_start
    day_num = min(cd_days, max(1, (pred_d - start_d).days + 1))
    return True, day_num, cd_days
