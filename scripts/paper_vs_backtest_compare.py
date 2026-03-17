#!/usr/bin/env python
"""
SignalFlow — השוואת Paper Trading ל-Backtest

בודק התאמה: ההחלטות שנשמרו ב-Paper תואמות את מה שה-backtest היה מחליט?
והתשואה המדומה מ-Paper קרובה לתשואת ה-backtest?

שימוש:
  python scripts/paper_vs_backtest_compare.py
  python scripts/paper_vs_backtest_compare.py --paper-json storage/paper_decisions.json --symbol AAPL
"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.pipeline import DataPipeline
from backtesting.engine import BacktestEngine


def _load_paper_decisions(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("decisions", [])


def _paper_simulated_return(decisions: list, symbol: str) -> dict:
    """
    Simulate return from Paper decisions: for each day with has_edge_final=True,
    apply next-day return with position_pct sizing.
    """
    if not decisions:
        return {"total_return": 0.0, "n_days": 0, "n_long": 0}
    dates = sorted({d["date"] for d in decisions if d.get("date")})
    if len(dates) < 2:
        return {"total_return": 0.0, "n_days": len(dates), "n_long": 0}
    start, end = dates[0], dates[-1]
    years = max(1, (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days / 365)
    period = f"{int(years)+1}y"
    try:
        pipeline = DataPipeline(symbol=symbol, horizon="daily", period=period, end_date=end)
        df = pipeline.run()
    except Exception as e:
        return {"error": str(e), "total_return": 0.0, "n_days": 0, "n_long": 0}
    returns = df["returns"].dropna()
    by_date = {d["date"]: d for d in decisions if d.get("date") and d.get("symbol", "").upper() == symbol.upper()}
    cum = 1.0
    n_long = 0
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
        cum *= 1 + pos_pct * next_ret
        n_long += 1
    total_ret = cum - 1.0
    return {"total_return": total_ret, "n_days": len(by_date), "n_long": n_long}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Compare Paper decisions vs Backtest")
    ap.add_argument("--paper-json", default=None, help="Path to paper_decisions.json")
    ap.add_argument("--symbol", default="AAPL", help="Symbol")
    args = ap.parse_args()

    root = Path(__file__).parent.parent
    paper_path = Path(args.paper_json) if args.paper_json else root / "storage" / "paper_decisions.json"
    decisions = _load_paper_decisions(paper_path)

    print("=" * 60)
    print("SignalFlow — Paper vs Backtest Comparison")
    print("=" * 60)
    print(f"Paper decisions: {paper_path}")
    print(f"Records: {len(decisions)}")
    if not decisions:
        print("\nNo paper decisions found. Run paper_trading_daily first (e.g. --batch-start/end)")
        return 1

    dates = sorted({d["date"] for d in decisions if d.get("date")})
    if not dates:
        print("No valid dates in paper decisions.")
        return 1
    start_d, end_d = dates[0], dates[-1]
    print(f"Date range: {start_d} to {end_d} ({len(dates)} days)")

    # Paper simulated return
    paper_res = _paper_simulated_return(decisions, args.symbol)
    if "error" in paper_res:
        print(f"\nPaper simulation error: {paper_res['error']}")
    else:
        print(f"\nPaper simulated: Return={paper_res['total_return']:.1%} | Long days={paper_res['n_long']}")

    # Backtest same period
    years = max(2, (datetime.strptime(end_d, "%Y-%m-%d") - datetime.strptime(start_d, "%Y-%m-%d")).days / 365)
    period = f"{int(years)+1}y"
    print(f"\nBacktest: period={period} end_date={end_d} mode=best_combo")
    engine = BacktestEngine(
        symbol=args.symbol,
        horizon="daily",
        use_ml=False,
        mean_rev_mult=2.0,
        atr_stop_mult=2.0,
        vol_target_ann=0.15,
    )
    result = engine.run(period=period, end_date=end_d)
    print(f"Backtest: Return={result.total_return:.1%} | Trades={result.n_trades} | Sharpe={result.sharpe_ratio:.3f}")

    # Compare
    if "error" not in paper_res and paper_res["n_long"] > 0:
        diff = abs(paper_res["total_return"] - result.total_return)
        print(f"\n--- Comparison ---")
        print(f"Return diff: {diff:.1%}")
        if diff < 0.05:
            print("OK: Paper and Backtest are aligned (diff < 5%)")
        elif diff < 0.15:
            print("Caution: Some discrepancy — check cross_asset, point-in-time alignment")
        else:
            print("Warning: Significant discrepancy — investigate Paper vs Backtest logic")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
