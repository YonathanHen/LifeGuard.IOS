"""
SignalFlow — Central Settings
"""
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
STORAGE_DIR = PROJECT_ROOT / "storage"

# Ensure storage structure
(STORAGE_DIR / "models").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "data").mkdir(parents=True, exist_ok=True)


def load_horizons() -> dict:
    """Load horizon parameters."""
    with open(CONFIG_DIR / "horizons.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_symbols() -> dict:
    """Load symbols config."""
    with open(CONFIG_DIR / "symbols.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


HORIZONS = load_horizons()
SYMBOLS = load_symbols()
