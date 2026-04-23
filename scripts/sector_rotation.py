#!/usr/bin/env python
"""
SignalFlow — Sector Rotation Strategy

Ranks sector ETFs by 6-month momentum, holds top 3-4. Rebalance monthly.
Standalone strategy — can run alongside best_combo on stocks.

Usage:
  python scripts/sector_rotation.py
  python scripts/sector_rotation.py --top 4 --lookback 6
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.fetchers import fetch_yahoo


def _load_sector_etfs() -> list:
    config = Path(__file__).parent.parent / "config" / "symbols.yaml"
    if not config.exists():
        return ["XLK", "XLV", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"]
    try:
        import yaml
        with open(config, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("sector_etfs", ["XLK", "XLV", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"])
    except Exception:
        return ["XLK", "XLV", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"]


def _compute_momentum(symbol: str, end_date: str, lookback_months: int) -> float | None:
    try:
        end_d = datetime.strptime(end_date, "%Y-%m-%d")
        start_d = end_d - timedelta(days=lookback_months * 22)
        raw = fetch_yahoo(
            symbol,
            start_date=start_d.strftime("%Y-%m-%d"),
            end_date=(end_d + timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if raw is None or raw.empty or len(raw) < 20:
            return None
        close = raw["Adj Close"] if "Adj Close" in raw.columns else raw["Close"]
        ret = (close.iloc[-1] / close.iloc[0]) - 1.0
        return float(ret)
    except Exception:
        return None


def run_sector_rotation(
    end_date: str | None = None,
    lookback_months: int = 6,
    top_n: int = 3,
) -> dict:
    """Rank sector ETFs by momentum, return top N."""
    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
    etfs = _load_sector_etfs()
    scored = []
    for sym in etfs:
        mom = _compute_momentum(sym, end_date, lookback_months)
        if mom is not None:
            scored.append({"symbol": sym, "momentum": mom})
    scored.sort(key=lambda x: x["momentum"], reverse=True)
    top = scored[:top_n]
    return {
        "date": end_date,
        "lookback_months": lookback_months,
        "top_n": top_n,
        "top_sectors": top,
        "all_ranked": scored,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Sector Rotation — rank ETFs by momentum")
    ap.add_argument("--end-date", default=None, help="End date YYYY-MM-DD")
    ap.add_argument("--lookback", type=int, default=6, help="Momentum lookback (months)")
    ap.add_argument("--top", type=int, default=3, help="Number of top sectors to hold")
    ap.add_argument("--out", default=None, help="Save JSON path")
    args = ap.parse_args()

    result = run_sector_rotation(end_date=args.end_date, lookback_months=args.lookback, top_n=args.top)

    print("=" * 60)
    print("SignalFlow — Sector Rotation")
    print("=" * 60)
    print(f"Date: {result['date']} | Lookback: {result['lookback_months']}mo | Top: {result['top_n']}")
    print("\nTop sectors (by momentum):")
    for i, s in enumerate(result["top_sectors"], 1):
        print(f"  {i}. {s['symbol']}: {s['momentum']:.1%}")
    print("\nAll ranked:")
    for s in result["all_ranked"]:
        print(f"  {s['symbol']}: {s['momentum']:.1%}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved: {args.out}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
