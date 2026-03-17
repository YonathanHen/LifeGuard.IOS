#!/usr/bin/env python
"""
SignalFlow — Run all new strategies and compare

Runs: baseline, MR x2, vol-target, ATR stop, Kelly, multi-symbol.
Saves to storage/strategy_compare_results.json and appends to docs.
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine

STORAGE = Path(__file__).parent.parent / "storage"
RESULTS_DIR = Path(__file__).parent.parent / "results"
STORAGE.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


STRATEGIES = [
    {
        "id": "baseline",
        "label": "Stat Only (baseline)",
        "kwargs": {"use_ml": False, "mean_rev_mult": 1.0},
    },
    {
        "id": "mr_x2",
        "label": "MR x2 (mean_rev_mult=2.0)",
        "kwargs": {"use_ml": False, "mean_rev_mult": 2.0},
    },
    {
        "id": "vol_target",
        "label": "Volatility Target 15%",
        "kwargs": {"use_ml": False, "vol_target_ann": 0.15},
    },
    {
        "id": "atr_stop",
        "label": "ATR Stop x2",
        "kwargs": {"use_ml": False, "atr_stop_mult": 2.0},
    },
    {
        "id": "kelly",
        "label": "Half Kelly sizing",
        "kwargs": {"use_ml": False, "kelly_frac": 0.5},
    },
    {
        "id": "mr_x2_vol",
        "label": "MR x2 + Vol Target",
        "kwargs": {"use_ml": False, "mean_rev_mult": 2.0, "vol_target_ann": 0.15},
    },
    # Combination strategies
    {
        "id": "mr_x2_atr",
        "label": "MR x2 + ATR Stop",
        "kwargs": {"use_ml": False, "mean_rev_mult": 2.0, "atr_stop_mult": 2.0},
    },
    {
        "id": "atr_vol",
        "label": "ATR Stop + Vol Target",
        "kwargs": {"use_ml": False, "atr_stop_mult": 2.0, "vol_target_ann": 0.15},
    },
    {
        "id": "mr_x2_atr_vol",
        "label": "MR x2 + ATR Stop + Vol Target",
        "kwargs": {"use_ml": False, "mean_rev_mult": 2.0, "atr_stop_mult": 2.0, "vol_target_ann": 0.15},
    },
]


def _get_git_commit() -> str:
    """Return current git commit hash for reproducibility."""
    try:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent, timeout=5
        )
        return out.stdout.strip()[:12] if out.returncode == 0 and out.stdout else ""
    except Exception:
        return ""


def _run_single(args: tuple) -> dict:
    """Run one backtest. Used for parallel execution."""
    symbol, period, end_date, strat_id, strat_kw = args
    base = {"symbol": symbol, "horizon": "daily", "refit_every": 5, "commission_bps": 5, "slippage_bps": 3}
    full_kw = {**base, **strat_kw}
    eng = BacktestEngine(**full_kw)
    result = eng.run(period=period, end_date=end_date)
    avg = (result.total_return / result.n_trades * 100) if result.n_trades else 0
    return {
        "strategy_id": strat_id,
        "symbol": symbol,
        "period": period,
        "end_date": end_date,
        "params": {k: v for k, v in full_kw.items() if k != "symbol"},
        "costs_included": True,
        "sharpe": round(result.sharpe_ratio, 4),
        "max_dd": round(result.max_drawdown, 4),
        "total_return": round(result.total_return, 4),
        "n_trades": result.n_trades,
        "hit_rate": round(result.hit_rate, 4),
        "avg_trade_pct": round(avg, 4),
    }


def _run_multi_symbol(symbols: list, period: str, end_date: str, strat_kw: dict) -> dict:
    """Run backtest for multiple symbols, return averaged metrics."""
    base = {"horizon": "daily", "refit_every": 5, "commission_bps": 5, "slippage_bps": 3}
    results = []
    for sym in symbols:
        eng = BacktestEngine(**{**base, "symbol": sym, **strat_kw})
        r = eng.run(period=period, end_date=end_date)
        results.append({
            "symbol": sym,
            "sharpe": r.sharpe_ratio,
            "return": r.total_return,
            "dd": r.max_drawdown,
            "trades": r.n_trades,
        })
    # Equal-weight portfolio return: (r1+r2+...+rn)/n
    ret_avg = sum(r["return"] for r in results) / len(results)
    sharpe_avg = sum(r["sharpe"] for r in results) / len(results)
    dd_avg = sum(r["dd"] for r in results) / len(results)
    trades_total = sum(r["trades"] for r in results)
    full_params = {"commission_bps": 5, "slippage_bps": 3, "refit_every": 5, **strat_kw, "symbols": symbols}
    return {
        "strategy_id": "multi_symbol",
        "symbol": ",".join(symbols),
        "period": period,
        "end_date": end_date,
        "params": full_params,
        "costs_included": True,
        "sharpe": round(sharpe_avg, 4),
        "max_dd": round(dd_avg, 4),
        "total_return": round(ret_avg, 4),
        "n_trades": trades_total,
        "hit_rate": None,
        "avg_trade_pct": None,
        "by_symbol": results,
    }


def main():
    ap = argparse.ArgumentParser(description="Run strategy comparison")
    ap.add_argument("--period", default="3y", help="Backtest period")
    ap.add_argument("--end-date", default=None, help="Pin end date")
    ap.add_argument("--symbol", default="AAPL", help="Single symbol")
    ap.add_argument("--symbols", default=None, help="Comma list for multi-symbol")
    ap.add_argument("--parallel", type=int, default=0, help="Max parallel workers (0=sequential)")
    ap.add_argument("--strategies", default=None, help="Comma ids to run (default: all)")
    args = ap.parse_args()

    to_run = [s for s in STRATEGIES if s["id"] != "multi_symbol"]
    if args.strategies:
        ids = {x.strip() for x in args.strategies.split(",")}
        to_run = [s for s in to_run if s["id"] in ids]

    print("=" * 60)
    print("SignalFlow — Strategy Comparison")
    print("=" * 60)
    print(f"Symbol: {args.symbol} | Period: {args.period}" + (f" | End: {args.end_date}" if args.end_date else ""))
    print(f"Strategies: {[s['id'] for s in to_run]}")
    print()

    git_commit = _get_git_commit()
    all_results = []
    for strat in to_run:
        print(f"  Running {strat['id']}...")
        res = _run_single((
            args.symbol, args.period, args.end_date,
            strat["id"], strat["kwargs"]
        ))
        res["label"] = strat["label"]
        res["timestamp"] = datetime.now().isoformat()
        res["git_commit"] = git_commit
        all_results.append(res)
        print(f"    Sharpe={res['sharpe']:.3f} Return={res['total_return']:.1%} DD={res['max_dd']:.1%} Trades={res['n_trades']}")

    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
        print(f"  Running multi_symbol ({symbols})...")
        res = _run_multi_symbol(symbols, args.period, args.end_date, {"use_ml": False})
        res["label"] = f"Multi-symbol {symbols}"
        res["timestamp"] = datetime.now().isoformat()
        res["git_commit"] = git_commit
        all_results.append(res)
        print(f"    Sharpe={res['sharpe']:.3f} Return={res['total_return']:.1%} DD={res['max_dd']:.1%}")

    # Save JSON
    out_path = STORAGE / "strategy_compare_results.json"
    data = {
        "runs": all_results,
        "last_updated": datetime.now().isoformat(),
        "git_commit": git_commit,
        "_costs_note": "All results include commission 5bps + slippage 3bps (0.16% round-trip)",
    }
    if out_path.exists():
        try:
            with open(out_path) as f:
                prev = json.load(f)
            prev["runs"] = prev.get("runs", []) + all_results
            prev["last_updated"] = data["last_updated"]
            prev["git_commit"] = data["git_commit"]
            prev["_costs_note"] = data["_costs_note"]
            data = prev
        except Exception:
            pass
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n[Saved: {out_path}]")

    # Append to doc
    doc_path = Path(__file__).parent.parent / "docs" / "STRATEGY_COMPARE_RESULTS.md"
    lines = [
        "",
        "## Run " + datetime.now().strftime("%Y-%m-%d %H:%M"),
        f"Period: {args.period}" + (f" | End: {args.end_date}" if args.end_date else ""),
        f"Symbol: {args.symbol}" + (f" (multi: {args.symbols})" if args.symbols else ""),
        "",
        "| Strategy | Sharpe | Return | Max DD | Trades | Params |",
        "|----------|--------|--------|--------|--------|--------|",
    ]
    for r in all_results:
        params = ", ".join(f"{k}={v}" for k, v in (r.get("params") or {}).items() if k != "symbol" and v is not None)
        lines.append(f"| {r.get('label', r['strategy_id'])} | {r['sharpe']:.3f} | {r['total_return']:.1%} | {r['max_dd']:.1%} | {r['n_trades']} | {params[:40]} |")
    lines.append("")
    with open(doc_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Appended to: {doc_path}]")

    # Best
    best = max(all_results, key=lambda x: (x["sharpe"], x["total_return"]))
    print(f"\n Best: {best['label']} — Sharpe {best['sharpe']:.3f}, Return {best['total_return']:.1%}")


if __name__ == "__main__":
    main()
