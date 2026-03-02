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
from data.fetchers.fred_fetcher import fetch_credit_spread, fetch_yield_curve, fetch_macro_data, fetch_yield_curve, fetch_macro_data


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

    # 2. Macro (Credit + Yield Curve)
    print("\n2. fetch_macro_data (credit_spread + yield_curve):")
    macro = fetch_macro_data(period="1y")
    if macro.empty:
        print("   -> Empty")
    else:
        print(f"   -> Columns: {list(macro.columns)}")
        if "yield_curve" in macro.columns:
            yc = macro["yield_curve"].dropna()
            if len(yc) > 0:
                print(f"   -> yield_curve range: {yc.min():.2f} - {yc.max():.2f}")

    # 3. Via Pipeline (with shift(1) for look-ahead prevention)
    print("\n3. Pipeline (AAPL, daily, 1y):")
    try:
        p = DataPipeline("AAPL", "daily", period="1y")
        df = p.run()
        print(f"   -> is_fred_available: {p.is_fred_available()}")
        fred_cols = [c for c in ["credit_spread", "yield_curve"] if c in df.columns]
        if fred_cols:
            for c in fred_cols:
                s = df[c].dropna()
                if len(s) == 0:
                    print(f"   -> {c}: all NaN")
                else:
                    print(f"   -> {c}: {len(s)} non-null, range {s.min():.2f} - {s.max():.2f}")
            print("\n   Last 5 rows (returns | credit_spread | yield_curve):")
            disp = ["returns"] + [c for c in fred_cols if c in df.columns]
            print(df[disp].tail(5).to_string())
        else:
            print("   -> FRED columns missing (FRED unavailable)")
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
