#!/usr/bin/env python
"""
SignalFlow — Strategy Degradation Check

Computes rolling Sharpe from paper_decisions and alerts if degradation detected.
Run weekly/monthly. Compares to expected backtest Sharpe.

Usage:
  python scripts/strategy_degradation_check.py
  python scripts/strategy_degradation_check.py --symbol AAPL --rolling-days 60 --min-sharpe 1.0
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.pipeline import DataPipeline


def _load_paper_decisions(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("decisions", [])


def _paper_daily_returns(decisions: list, symbol: str, end_date: str) -> list:
    """Return list of (date_str, daily_ret) for days we were long."""
    if not decisions:
        return []
    dates = sorted({d["date"] for d in decisions if d.get("date")})
    if len(dates) < 2:
        return []
    start, end = dates[0], dates[-1]
    if end_date:
        end = min(end, end_date)
    years = max(1, (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days / 365)
    period = f"{int(years)+1}y"
    try:
        pipeline = DataPipeline(symbol=symbol, horizon="daily", period=period, end_date=end)
        df = pipeline.run()
    except Exception as e:
        return []
    returns = df["returns"].dropna()
    by_date = {d["date"]: d for d in decisions if d.get("date") and d.get("symbol", "").upper() == symbol.upper()}
    out = []
    for i in range(len(returns) - 1):
        dt = returns.index[i]
        dt_str = dt.strftime("%Y-%m-%d")
        if dt_str not in by_date:
            continue
        rec = by_date[dt_str]
        if not rec.get("has_edge_final", False):
            continue
        pos_pct = rec.get("position_pct", 100) / 100.0
        next_ret = returns.iloc[i + 1]
        out.append((dt_str, pos_pct * next_ret))
    return out


def _rolling_sharpe(returns: list, window: int) -> float | None:
    """Sharpe of last `window` returns. Annualized (sqrt(252))."""
    if len(returns) < window:
        return None
    subset = [r for _, r in returns[-window:]]
    if not subset:
        return None
    mean = sum(subset) / len(subset)
    var = sum((r - mean) ** 2 for r in subset) / max(1, len(subset) - 1)
    std = (var ** 0.5) if var > 0 else 0.0
    if std < 1e-8:
        return None
    return mean / std * (252 ** 0.5)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Strategy Degradation Check — rolling Sharpe vs expected")
    ap.add_argument("--paper-json", default=None, help="Path to paper_decisions.json")
    ap.add_argument("--symbol", default="AAPL", help="Symbol")
    ap.add_argument("--rolling-days", type=int, default=60, help="Rolling window for Sharpe")
    ap.add_argument("--min-sharpe", type=float, default=1.0, help="Alert if rolling Sharpe < this (expected ~1.99 for best_combo)")
    ap.add_argument("--end-date", default=None, help="End date YYYY-MM-DD")
    args = ap.parse_args()

    root = Path(__file__).parent.parent
    paper_path = Path(args.paper_json) if args.paper_json else root / "storage" / "paper_decisions.json"
    decisions = _load_paper_decisions(paper_path)

    print("=" * 60)
    print("SignalFlow — Strategy Degradation Check")
    print("=" * 60)
    print(f"Paper: {paper_path} | Symbol: {args.symbol}")
    if not decisions:
        print("No paper decisions. Run paper_trading_daily first.")
        return 0

    daily = _paper_daily_returns(decisions, args.symbol, args.end_date)
    if len(daily) < args.rolling_days:
        print(f"Need >={args.rolling_days} long-days, have {len(daily)}")
        return 0

    sharpe = _rolling_sharpe(daily, args.rolling_days)
    if sharpe is None:
        print("Could not compute Sharpe.")
        return 0

    total_ret = 1.0
    for _, r in daily:
        total_ret *= 1 + r
    total_ret -= 1.0

    print(f"\nRolling Sharpe ({args.rolling_days}d): {sharpe:.3f}")
    print(f"Total return (paper): {total_ret:.1%}")
    print(f"Long days: {len(daily)}")
    print(f"Min Sharpe threshold: {args.min_sharpe}")

    if sharpe < args.min_sharpe:
        print(f"\n[ALERT] DEGRADATION: Rolling Sharpe {sharpe:.3f} < {args.min_sharpe}")
        print("   Consider: pause trading, review Paper vs Backtest, check data/params.")
    else:
        print(f"\n[OK] Rolling Sharpe {sharpe:.3f} >= {args.min_sharpe}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
