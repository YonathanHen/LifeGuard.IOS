#!/usr/bin/env python
"""
SignalFlow — אימות נתוני FRED (Credit Spread)
בודק שהפיצר credit_spread מגיע נכון מהמערכת.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from data.pipeline import DataPipeline
from data.fetchers.fred_fetcher import fetch_credit_spread


def main():
    print("=" * 50)
    print("SignalFlow — FRED Data Validation")
    print("=" * 50)

    has_key = bool(os.environ.get("FRED_API_KEY"))
    print(f"\nFRED_API_KEY set: {has_key}")

    # 1. Direct fetcher
    print("\n1. Direct fetch_credit_spread(period='1y'):")
    credit = fetch_credit_spread(period="1y")
    if credit.empty:
        print("   -> Empty (no key or fetch failed)")
    else:
        print(f"   -> Rows: {len(credit)}")
        print(f"   -> Date range: {credit.index.min()} to {credit.index.max()}")
        print(f"   -> Value range: {credit.min():.2f} - {credit.max():.2f} (typical: 3-8%)")
        print(f"   -> Last 5 values:\n{credit.tail()}")

    # 2. Via Pipeline
    print("\n2. Pipeline (AAPL, daily, 1y):")
    try:
        p = DataPipeline("AAPL", "daily", period="1y")
        df = p.run()
        print(f"   -> is_fred_available: {p.is_fred_available()}")
        if "credit_spread" in df.columns:
            cr = df["credit_spread"].dropna()
            if len(cr) == 0:
                print("   -> credit_spread: all NaN")
            else:
                print(f"   -> credit_spread: {len(cr)} non-null rows")
                print(f"   -> Range: {cr.min():.2f} - {cr.max():.2f}")
                print("\n   Last 10 rows (returns | credit_spread):")
                print(df[["returns", "credit_spread"]].tail(10).to_string())
        else:
            print("   -> credit_spread: column missing (FRED unavailable)")
    except Exception as e:
        print(f"   -> Error: {e}")

    print("\n" + "=" * 50)
    if has_key and not credit.empty:
        print("Validation: OK - FRED data flowing correctly")
    elif has_key and credit.empty:
        print("Validation: FAIL - Key set but no data. Check API key, network.")
    else:
        print("Validation: SKIP - Set FRED_API_KEY to test. Get free key: https://fred.stlouisfed.org/docs/api/api_key.html")
    print("=" * 50)


if __name__ == "__main__":
    main()
