"""
SignalFlow — Event Calendar Filter

Skip or reduce position on earnings, FOMC, CPI, etc.
Data: config/event_calendar.json
"""
import json
from pathlib import Path
from typing import Set


def _load_event_dates(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "event_calendar.json"
    if not config_path.exists():
        return {"global": [], "AAPL": [], "SPY": [], "QQQ": []}
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return {"global": [], "AAPL": [], "SPY": [], "QQQ": []}


def is_event_day(date_str: str, symbol: str, config_path: Path | None = None) -> bool:
    """
    Check if date is an event day (earnings, FOMC, etc.) for this symbol.

    Returns True if we should skip or reduce position.
    """
    data = _load_event_dates(config_path)
    symbol = symbol.upper()
    global_dates = set(data.get("global", []))
    symbol_dates = set(data.get(symbol, []))
    all_events = global_dates | symbol_dates
    return date_str in all_events
