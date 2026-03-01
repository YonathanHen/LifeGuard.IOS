#!/usr/bin/env python
"""
SignalFlow — Train LSTM Model (Phase 2B)
Trains on pipeline data (returns + VIX + credit_spread).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from data.pipeline import DataPipeline
from models.ml.lstm_model import LSTMPredictor


def main():
    symbol = os.environ.get("LSTM_TRAIN_SYMBOL", "AAPL")
    horizon = os.environ.get("LSTM_TRAIN_HORIZON", "daily")
    period = os.environ.get("LSTM_TRAIN_PERIOD", "5y")

    print("=" * 50)
    print("SignalFlow — LSTM Training")
    print("=" * 50)
    print(f"Symbol: {symbol} | Horizon: {horizon} | Period: {period}")

    pipeline = DataPipeline(symbol=symbol, horizon=horizon, period=period)
    df = pipeline.run()

    print(f"Rows: {len(df)}")
    cols = ["returns", "vix", "credit_spread"]
    for c in cols:
        print(f"  {c}: {'Y' if c in df.columns else 'N (fallback)'}")

    predictor = LSTMPredictor(lookback=40)
    result = predictor.fit(df, epochs=80, lr=0.001, batch_size=32, val_frac=0.2)

    if "error" in result:
        print(f"\nError: {result['error']}")
        return 1

    print(f"\nTrain loss: {result['train_loss']:.4f} | Val loss: {result['val_loss']:.4f}")
    print("Model saved to storage/lstm_model.pt")

    # Quick predict test
    probs = predictor.predict_proba(df)
    if probs:
        print(f"\nSample prediction (last row): P_up={probs['P_up']:.3f} | P_down={probs['P_down']:.3f} | P_flat={probs['P_flat']:.3f}")

    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
