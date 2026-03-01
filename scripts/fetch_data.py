#!/usr/bin/env python
"""
SignalFlow — Fetch data script
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.pipeline import DataPipeline


def main():
    symbol = "AAPL"
    horizon = "daily"
    print(f"Fetching {symbol} ({horizon})...")
    pipeline = DataPipeline(symbol=symbol, horizon=horizon)
    df = pipeline.run()
    print(f"Got {len(df)} rows")
    print(df.tail())


if __name__ == "__main__":
    main()
