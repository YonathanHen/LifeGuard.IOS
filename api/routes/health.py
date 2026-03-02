"""SignalFlow — Health check."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "SignalFlow"}


@router.get("/health/ml-status")
def ml_status():
    """LSTM model freshness — for Alpha Decay monitoring. Run walk_forward_retrain if stale."""
    try:
        from models.ml.train_info import get_lstm_train_info
        info = get_lstm_train_info()
        if info:
            return {"ml_model": "ok", **info}
        return {"ml_model": "none", "message": "No LSTM model found"}
    except Exception as e:
        return {"ml_model": "error", "message": str(e)}
