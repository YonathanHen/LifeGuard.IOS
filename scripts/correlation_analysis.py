#!/usr/bin/env python
"""
SignalFlow — Correlation Analysis
Checks if Credit Spread and Yield Curve correlate with stock returns.
Goal: understand if External Features add signal before relying on them in LSTM.

Usage:
  python scripts/correlation_analysis.py
  python scripts/correlation_analysis.py --csv path/to/data.csv
  CORR_SYMBOL=MSFT CORR_PERIOD=3y python scripts/correlation_analysis.py
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import pandas as pd
import numpy as np
from data.pipeline import DataPipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="Load from CSV instead of pipeline (columns: returns, vix, credit_spread, yield_curve)")
    args = ap.parse_args()

    symbol = os.environ.get("CORR_SYMBOL", "AAPL")
    period = os.environ.get("CORR_PERIOD", "5y")
    horizon = "daily"

    print("=" * 60)
    print("SignalFlow — Correlation Analysis")
    if args.csv:
        print(f"Source: CSV file")
    else:
        print(f"Symbol: {symbol} | Period: {period} | Horizon: {horizon}")
    print("=" * 60)

    if args.csv:
        df = pd.read_csv(args.csv, index_col=0, parse_dates=True)
        if "returns" not in df.columns:
            print("CSV must have 'returns' column. Use pipeline output.")
            return 1
    else:
        try:
            p = DataPipeline(symbol=symbol, horizon=horizon, period=period)
            df = p.run()
        except Exception as e:
            print(f"Error loading data: {e}")
            print("  (Yahoo Finance may be rate-limited. Try again in a few minutes.)")
            print("  Or use --csv path/to/exported_data.csv")
            return 1

    cols = ["returns", "volatility"]
    if "vix" in df.columns:
        cols.append("vix")
    if "credit_spread" in df.columns:
        cols.append("credit_spread")
    if "yield_curve" in df.columns:
        cols.append("yield_curve")

    df_corr = df[cols].dropna()
    if len(df_corr) < 100:
        print("Insufficient data for correlation")
        return 1

    # 1. Correlation matrix (levels)
    corr = df_corr.corr()

    print("\n--- Correlation Matrix (contemporaneous) ---")
    print(corr.round(3).to_string())

    # 2. Correlation with FORWARD return (target)
    df_corr["returns_fwd"] = df_corr["returns"].shift(-1)
    df_fwd = df_corr.dropna(subset=["returns_fwd"])

    fwd_corr = {}
    for c in cols:
        if c != "returns":
            r = df_fwd[c].corr(df_fwd["returns_fwd"])
            fwd_corr[c] = r

    print("\n--- Correlation with Forward Return (next period) ---")
    print("    (feature today vs return tomorrow)")
    for col, r in sorted(fwd_corr.items(), key=lambda x: -abs(x[1])):
        bar = "#" * int(abs(r) * 30) + " " * (30 - int(abs(r) * 30))
        sign = "+" if r > 0 else "-"
        print(f"  {col:18} {r:+.3f} {sign}{bar}")

    # 3. Lagged correlation (feature t-1 vs return t)
    print("\n--- Lagged Correlation (feature yesterday vs return today) ---")
    df_corr["returns_fwd"] = df_corr["returns"].shift(-1)
    for c in cols:
        if c == "returns":
            continue
        df_corr[f"{c}_lag1"] = df_corr[c].shift(1)
    df_lag = df_corr.dropna(subset=["returns_fwd"])
    lag_corr = {}
    for c in cols:
        if c != "returns" and f"{c}_lag1" in df_lag.columns:
            r = df_lag[f"{c}_lag1"].corr(df_lag["returns_fwd"])
            lag_corr[c] = r

    for col, r in sorted(lag_corr.items(), key=lambda x: -abs(x[1])):
        bar = "#" * int(abs(r) * 30) + " " * (30 - int(abs(r) * 30))
        sign = "+" if r > 0 else "-"
        print(f"  {col:18} {r:+.3f} {sign}{bar}")

    # 4. Summary
    print("\n--- Summary ---")
    ext_cols = [c for c in ["credit_spread", "yield_curve"] if c in fwd_corr]
    if ext_cols:
        best_ext = max(ext_cols, key=lambda c: abs(fwd_corr.get(c, 0)))
        r_ext = fwd_corr[best_ext]
        if abs(r_ext) < 0.05:
            print("  External features show weak correlation with forward returns.")
            print("  May still add signal in non-linear (LSTM) context.")
        elif abs(r_ext) > 0.15:
            print(f"  {best_ext} has meaningful correlation ({r_ext:+.2f}) with next return.")
        else:
            print(f"  {best_ext}: moderate correlation ({r_ext:+.2f}).")
    else:
        print("  No FRED data - run with FRED_API_KEY for credit_spread, yield_curve.")

    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
