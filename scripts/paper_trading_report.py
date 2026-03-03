#!/usr/bin/env python
"""
SignalFlow — Paper Trading Gate 2 Report
Computes Decision Consistency, Blocked Loss Rate, Net EV, Exposure.
Run weekly/monthly. Requires paper_decisions.json from paper_trading_daily.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from backtesting.engine import BacktestEngine


def _load_decisions(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _decision_consistency(decisions: list, symbol: str = "AAPL") -> float:
    """Fraction of days where has_edge_final did NOT flip from previous day."""
    by_date = sorted(
        (d for d in decisions if d.get("symbol") == symbol and d.get("date")),
        key=lambda d: d["date"],
    )
    if len(by_date) < 2:
        return 1.0
    flips = 0
    for i in range(1, len(by_date)):
        if by_date[i].get("has_edge_final") != by_date[i - 1].get("has_edge_final"):
            flips += 1
    return 1.0 - (flips / (len(by_date) - 1))


def _avg_holding_period(decisions: list, symbol: str = "AAPL") -> float:
    """Average consecutive days with has_edge_final=True."""
    by_date = sorted(
        (d for d in decisions if d.get("symbol") == symbol and d.get("date")),
        key=lambda d: d["date"],
    )
    if not by_date:
        return 0.0
    runs = []
    cur = 0
    for d in by_date:
        if d.get("has_edge_final"):
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    return sum(runs) / len(runs) if runs else 0.0


def _exposure_pct(decisions: list, symbol: str = "AAPL") -> float:
    """% days with has_edge_final=True."""
    relevant = [d for d in decisions if d.get("symbol") == symbol and d.get("date")]
    if not relevant:
        return 0.0
    in_market = sum(1 for d in relevant if d.get("has_edge_final"))
    return 100.0 * in_market / len(relevant)


def _check_data_alignment(
    decisions: list, backtest_dates: list, symbol: str
) -> list[str]:
    """Return list of warnings if paper dates mismatch backtest data."""
    warnings = []
    paper_dates = {d["date"] for d in decisions if d.get("symbol") == symbol}
    backtest_set = {d.strftime("%Y-%m-%d") for d in backtest_dates}
    missing_in_backtest = paper_dates - backtest_set
    if missing_in_backtest:
        warnings.append(
            f"תאריכים ב-paper_decisions חסרים ב-Yahoo: {sorted(missing_in_backtest)[:5]}..."
        )
    return warnings


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Paper Trading — Gate 2 report")
    ap.add_argument("--symbol", default="AAPL")
    ap.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    ap.add_argument("--period", default="3y", help="Backtest period (default 3y)")
    ap.add_argument("--no-save", action="store_true", help="Do not save paper_metrics.json")
    args = ap.parse_args()

    storage = Path(__file__).parent.parent / "storage"
    decisions_path = storage / "paper_decisions.json"
    decisions = _load_decisions(decisions_path)

    if not decisions:
        print("אין נתונים ב-paper_decisions.json. הרץ paper_trading_daily.py קודם.")
        sys.exit(1)

    by_symbol = [d for d in decisions if d.get("symbol") == args.symbol]
    if not by_symbol:
        print(f"אין החלטות ל-{args.symbol}")
        sys.exit(1)

    dates = sorted(d["date"] for d in by_symbol if d.get("date"))
    start = args.start or dates[0]
    end = args.end or dates[-1]

    delta = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days
    if delta < 90:
        print(f"⚠️ תקופה קצרה מדי ({delta} ימים). מינימום 3 חודשים ל-Gate 3.")

    disaster_threshold = float(
        os.environ.get("ML_NEGATIVE_FILTER_THRESHOLD")
        or os.environ.get("ML_DISASTER_THRESHOLD", "0.80")
    )

    engine = BacktestEngine(
        symbol=args.symbol,
        horizon="daily",
        use_ml=True,
        ml_negative_filter=True,
        ml_disaster_threshold=disaster_threshold,
    )

    period = args.period
    err = engine.error_type_analysis(
        period=period,
        disaster_threshold=disaster_threshold,
        end_date=end,
    )

    # Data alignment: compare paper_dates with Yahoo backtest range
    from data.pipeline import DataPipeline
    pipe = DataPipeline(args.symbol, "daily", period=period, end_date=end)
    df = pipe.run()
    returns = df["returns"].dropna()
    train_min = 252
    backtest_dates = list(returns.index[train_min : len(returns) - 1])

    alignment_warnings = _check_data_alignment(by_symbol, backtest_dates, args.symbol)

    decision_consistency = _decision_consistency(decisions, args.symbol)
    avg_holding = _avg_holding_period(decisions, args.symbol)
    exposure = _exposure_pct(decisions, args.symbol)

    gate2 = {
        "decision_consistency": round(decision_consistency, 4),
        "avg_holding_period_days": round(avg_holding, 2),
        "blocked_loss_rate": round(err.get("blocked_loss_rate", 0), 4),
        "net_ev": round(err.get("net_ev", 0), 4),
        "exposure_pct": round(exposure, 2),
        "sum_saved": round(err.get("sum_saved", 0), 4),
        "sum_missed": round(err.get("sum_missed", 0), 4),
    }

    if gate2["blocked_loss_rate"] > 0.5 and gate2["net_ev"] >= 0 and decision_consistency >= 0.5:
        go_no_go = "GO"
    elif gate2["net_ev"] < 0 or gate2["blocked_loss_rate"] < 0.5:
        go_no_go = "NO-GO"
    else:
        go_no_go = "PENDING"

    report = {
        "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "period": {"start": start, "end": end, "days": delta},
        "gate2": gate2,
        "go_no_go": go_no_go,
        "alignment_warnings": alignment_warnings,
    }

    print("=" * 60)
    print("SignalFlow — Paper Trading Gate 2 Report")
    print("=" * 60)
    print(f"  Symbol: {args.symbol}  Period: {start} → {end} ({delta} days)")
    print()
    print("  Gate 2 Metrics:")
    print(f"    Decision Consistency:  {gate2['decision_consistency']:.2%}")
    print(f"    Avg Holding Period:   {gate2['avg_holding_period_days']:.1f} days")
    print(f"    Blocked Loss Rate:    {gate2['blocked_loss_rate']:.2%}")
    print(f"    Net EV:               {gate2['net_ev']:.4f} ({gate2['net_ev']*100:.2f}%)")
    print(f"    Exposure:             {gate2['exposure_pct']:.1f}%")
    print()
    print(f"  Go/No-Go: {go_no_go}")
    if alignment_warnings:
        print()
        for w in alignment_warnings:
            print(f"  ⚠️ {w}")
    print("=" * 60)

    if not args.no_save:
        metrics_path = storage / "paper_metrics.json"
        metrics_history = []
        if metrics_path.exists():
            try:
                with open(metrics_path, encoding="utf-8") as f:
                    data = json.load(f)
                metrics_history = data if isinstance(data, list) else [data]
            except Exception:
                pass
        metrics_history.append(report)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_history, f, indent=2, ensure_ascii=False)
        print(f"  Saved: {metrics_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
