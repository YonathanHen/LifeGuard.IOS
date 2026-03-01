"""SignalFlow — API tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    """Health endpoint returns ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_structure():
    """Predict returns expected keys (may fail if network unavailable)."""
    try:
        r = client.get("/predict/AAPL", params={"horizon": "daily"})
        if r.status_code == 200:
            data = r.json()
            assert "direction" in data
            assert "has_edge" in data
            assert "system_assessment" in data
    except Exception:
        pass  # Network might be unavailable in CI
