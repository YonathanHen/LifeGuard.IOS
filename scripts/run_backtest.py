#!/usr/bin/env python
"""
SignalFlow — Run backtest

Modes from config/backtest_modes.json. Default: stat_only (the proven profitable baseline).
Docs: docs/BACKTEST_MODES.md | docs/BASELINE_PROTOCOL.md
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine

CONFIG_PATH = Path(__file__).parent.parent / "config" / "backtest_modes.json"
RESULTS_DIR = Path(__file__).parent.parent / "results"


def _bool_arg(val, default):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes")


def _save_run(mode: str, symbol: str, period: str, result, avg_trade: float, engine_kw: dict):
    """Save run to results/ (flight log)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    fname = f"{ts}_{symbol}_{mode}.json"
    path = RESULTS_DIR / fname
    data = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "symbol": symbol,
        "period": period,
        "sharpe": round(result.sharpe_ratio, 4),
        "max_dd": round(result.max_drawdown, 4),
        "total_return": round(result.total_return, 4),
        "n_trades": result.n_trades,
        "avg_trade_pct": round(avg_trade, 4),
        "hit_rate": round(result.hit_rate, 4),
        "params": {k: v for k, v in engine_kw.items() if k != "symbol"},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n[Saved: {path.relative_to(RESULTS_DIR.parent)}]")


def _load_mode(name: str) -> dict:
    """Load mode params from config. Keys starting with _ are ignored."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH) as f:
        data = json.load(f)
    modes = data.get("modes", {})
    cfg = dict(modes.get(name, {}))
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def main():
    ap = argparse.ArgumentParser(
        description="SignalFlow Backtest — use --mode to switch config. Default: stat_only."
    )
    ap.add_argument("--mode", default="stat_only", help="Mode from config/backtest_modes.json")
    ap.add_argument("--list-modes", action="store_true", help="List available modes and exit")
    ap.add_argument("--smoke", action="store_true", help="Quick smoke test: 2y period (~2 min)")
    ap.add_argument("--period", default=None, help="Override period (2y, 3y, 5y)")
    ap.add_argument("--symbol", default=None, help="Override symbol (AAPL, MSFT, ...)")
    ap.add_argument("--use-ml", nargs="?", const="true", metavar="true|false",
        help="Override use_ml. --use-ml or --use-ml true = on")
    ap.add_argument("--ml-threshold", type=float, default=None)
    ap.add_argument("--ml-negative-filter", nargs="?", const="true", metavar="true|false", default=None)
    ap.add_argument("--disaster-threshold", type=float, default=None)
    ap.add_argument("--commission", type=float, default=None, help="Commission bps")
    ap.add_argument("--slippage", type=float, default=None, help="Slippage bps")
    ap.add_argument("--end-date", type=str, default=None, help="Pin end date (YYYY-MM-DD) to reproduce a specific run. Default: today.")
    args = ap.parse_args()

    if args.list_modes:
        if not CONFIG_PATH.exists():
            print("No config at", CONFIG_PATH)
            return
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        modes = data.get("modes", {})
        for name in modes:
            obs = modes[name].get("_observed_3y") or modes[name].get("_observed_2y") or modes[name].get("_observed") or ""
            print(f"  {name}: {obs[:60]}..." if len(obs) > 60 else f"  {name}: {obs}")
        return

    cfg = _load_mode(args.mode)
    symbol = args.symbol or cfg.get("symbol", "AAPL")
    period = "2y" if args.smoke else (args.period or cfg.get("period", "3y"))

    engine_kw = {
        "symbol": symbol,
        "horizon": "daily",
        "refit_every": cfg.get("refit_every", 5),
        "use_ml": _bool_arg(args.use_ml, cfg.get("use_ml", False)),
        "ml_threshold": args.ml_threshold if args.ml_threshold is not None else cfg.get("ml_threshold", 0.6),
        "ml_negative_filter": _bool_arg(args.ml_negative_filter, cfg.get("ml_negative_filter", False)),
        "ml_disaster_threshold": args.disaster_threshold if args.disaster_threshold is not None else cfg.get("ml_disaster_threshold", 0.8),
        "commission_bps": args.commission if args.commission is not None else cfg.get("commission_bps", 5),
        "slippage_bps": args.slippage if args.slippage is not None else cfg.get("slippage_bps", 3),
    }

    print(f"Backtest: mode={args.mode} | {symbol} | {period}" + (f" end={args.end_date}" if args.end_date else ""))
    print(f"  use_ml={engine_kw['use_ml']} ml_threshold={engine_kw['ml_threshold']}")
    engine = BacktestEngine(**engine_kw)
    result = engine.run(period=period, end_date=args.end_date)

    avg_trade = (result.total_return / result.n_trades * 100) if result.n_trades else 0
    print("\n--- Backtest Results ---")
    print(f"Sharpe Ratio:    {result.sharpe_ratio:.3f}")
    print(f"Max Drawdown:    {result.max_drawdown:.1%}")
    print(f"Total Return:    {result.total_return:.1%}")
    print(f"Number of Trades: {result.n_trades}")
    print(f"Avg per trade:   {avg_trade:.3f}%")
    print(f"Hit Rate (long): {result.hit_rate:.1%}")

    # Flight log: save every run
    _save_run(args.mode, symbol, period, result, avg_trade, engine_kw)

    # Regression check: stat_only baseline
    if args.mode == "stat_only" and period >= "2y" and result.total_return < 0.12:
        print("\n⚠️ Regression? stat_only return < 12%. Expected ~20-24%. Check engine changes.")


if __name__ == "__main__":
    main()
