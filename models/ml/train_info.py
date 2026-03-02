"""LSTM training metadata — for freshness checks."""
import json
from datetime import datetime
from pathlib import Path


def _storage_path() -> Path:
    return Path(__file__).parent.parent.parent / "storage"


def get_lstm_train_info() -> dict | None:
    """
    Read LSTM train metadata (from walk_forward or train_lstm).
    Returns {train_date, data_end_date, symbol, period, days_ago, stale} or None.
    """
    info_path = _storage_path() / "lstm_train_info.json"
    if info_path.exists():
        try:
            with open(info_path) as f:
                info = json.load(f)
            s = info.get("train_date") or info.get("data_end_date")
            if s:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
                days_ago = (datetime.utcnow() - dt).days
                info["days_ago"] = days_ago
                info["stale"] = days_ago >= 90
                return info
        except Exception:
            pass
    model_path = _storage_path() / "lstm_model.pt"
    if model_path.exists():
        try:
            mtime = model_path.stat().st_mtime
            dt = datetime.utcfromtimestamp(mtime)
            days_ago = (datetime.utcnow() - dt).days
            return {
                "train_date": dt.isoformat() + "Z",
                "days_ago": days_ago,
                "stale": days_ago >= 90,
            }
        except Exception:
            pass
    return None
