#!/usr/bin/env python
"""
SignalFlow — Walk-Forward LSTM Retrain
Retrains LSTM on rolling window to combat Alpha Decay.
Run quarterly (or monthly) via cron/Task Scheduler.

Usage:
  python scripts/walk_forward_retrain.py
  python scripts/walk_forward_retrain.py --period 5y --end-date 2025-12-31
  python scripts/walk_forward_retrain.py --check    # Report days since last train
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from data.pipeline import DataPipeline
from models.ml.lstm_model import LSTMPredictor


def _model_path() -> Path:
    return Path(__file__).parent.parent / "storage" / "lstm_model.pt"


def _get_train_date() -> datetime | None:
    """Read train_date from lstm_train_info.json, model meta, or file mtime."""
    base = _model_path().parent
    # Prefer lstm_train_info.json (written by walk_forward)
    info_path = base / "lstm_train_info.json"
    if info_path.exists():
        try:
            import json
            with open(info_path) as f:
                info = json.load(f)
            s = info.get("train_date") or info.get("data_end_date")
            if s:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
    # Fallback: model meta or file mtime
    path = _model_path()
    if path.exists():
        try:
            import torch
            ckpt = torch.load(path, map_location="cpu", weights_only=True)
            meta = ckpt.get("meta", {})
            s = meta.get("train_date") or meta.get("data_end_date")
            if s:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
        mtime = path.stat().st_mtime
        return datetime.utcfromtimestamp(mtime)
    return None


def cmd_check(stale_days: int = 90) -> int:
    """Check if model needs retrain (older than stale_days)."""
    dt = _get_train_date()
    if dt is None:
        print("No model found. Run: python scripts/walk_forward_retrain.py")
        return 1
    delta = (datetime.utcnow() - dt).days
    print(f"LSTM last trained: {dt.date()} ({delta} days ago)")
    if delta >= stale_days:
        print(f"  [!!] Older than {stale_days} days — recommend retrain")
        return 1
    print(f"  [OK] Within {stale_days}-day window")
    return 0


def cmd_retrain(
    symbol: str = "AAPL",
    horizon: str = "daily",
    period: str = "5y",
    end_date: str | None = None,
    epochs: int = 80,
    dry_run: bool = False,
) -> int:
    """Run Walk-Forward retrain."""
    end = end_date or datetime.utcnow().strftime("%Y-%m-%d")
    print("=" * 55)
    print("SignalFlow — Walk-Forward LSTM Retrain")
    print("=" * 55)
    print(f"Symbol: {symbol} | Horizon: {horizon} | Window: {period} ending {end}")
    if dry_run:
        print("[DRY RUN — no training]")
        return 0

    pipeline = DataPipeline(symbol=symbol, horizon=horizon, period=period, end_date=end)
    df = pipeline.run()

    if len(df) < 300:
        print(f"Error: Need ~300+ rows, got {len(df)}")
        return 1

    cols = ["returns", "vix", "credit_spread", "yield_curve"]
    for c in cols:
        print(f"  {c}: {'Y' if c in df.columns else 'N (fallback)'}")

    predictor = LSTMPredictor(lookback=40)
    train_meta = {
        "train_date": datetime.utcnow().isoformat() + "Z",
        "data_end_date": end,
        "symbol": symbol,
        "period": period,
    }
    result = predictor.fit(
        df,
        epochs=epochs,
        lr=0.001,
        batch_size=32,
        val_frac=0.2,
        train_meta=train_meta,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        return 1

    # Save train info for API/dashboard (no torch needed to read)
    info_path = _model_path().parent / "lstm_train_info.json"
    import json
    with open(info_path, "w") as f:
        json.dump({**train_meta, "train_loss": result["train_loss"], "val_loss": result["val_loss"]}, f, indent=2)

    print(f"\nTrain loss: {result['train_loss']:.4f} | Val loss: {result['val_loss']:.4f}")
    print(f"Model saved to {_model_path()}")
    print(f"Train info: {info_path}")
    print("=" * 55)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Walk-Forward LSTM retrain (quarterly)")
    ap.add_argument("--check", action="store_true", help="Check if model is stale")
    ap.add_argument("--stale-days", type=int, default=90, help="Stale threshold (default 90)")
    ap.add_argument("--period", default="5y", help="Rolling window (default 5y)")
    ap.add_argument("--end-date", help="End date for data (default: today)")
    ap.add_argument("--symbol", default="AAPL", help="Symbol")
    ap.add_argument("--epochs", type=int, default=80, help="Training epochs")
    ap.add_argument("--dry-run", action="store_true", help="No training, just validate")
    args = ap.parse_args()

    if args.check:
        return cmd_check(stale_days=args.stale_days)
    return cmd_retrain(
        symbol=args.symbol,
        period=args.period,
        end_date=args.end_date,
        epochs=args.epochs,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
