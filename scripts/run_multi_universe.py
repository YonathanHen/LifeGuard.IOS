#!/usr/bin/env python
"""
SignalFlow — Multi-Stock Universe Backtest

Default: **best_combo** (mean_rev_mult, ATR, vol_target) — same as before.

Optional **--profile production**: same engine defaults as `run_backtest_with_ml.py`
(Stat+ML negative filter, optional --low-vol-tilt / --dual-momentum).

Usage:
  python scripts/run_multi_universe.py
  python scripts/run_multi_universe.py --period 3y --end-date 2026-03-02
  python scripts/run_multi_universe.py --profile production --period 3y --limit 10 --low-vol-tilt
  python scripts/run_multi_universe.py --profile production --no-ml --limit 5

פלט JSON: אם לא מועבר --out, נשמר אוטומטית תחת run_outputs/research_runs/ (ראו run_outputs/README.md).

דירוג יקום (שלב 2 — docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md):
  python scripts/run_multi_universe.py --from-rank-json run_outputs/rankings/universe_rank_2026-04-21_123456.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

# BacktestEngine: train_min_days (252) + 50 — ראו backtesting/engine.py
_ENGINE_MIN_TRADING_DAYS = 302

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.engine import BacktestEngine

SCHEMA_RANK_V1 = "signalflow.universe_rank.v1"


def _load_universe() -> list:
    config = Path(__file__).parent.parent / "config" / "symbols.yaml"
    if not config.exists():
        return ["AAPL", "MSFT", "GOOGL", "SPY"]
    try:
        import yaml
        with open(config, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("universe", data.get("primary", ["AAPL", "MSFT", "GOOGL", "SPY"]))
    except Exception:
        return ["AAPL", "MSFT", "GOOGL", "SPY"]


def _load_symbols_from_rank_json(path: Path, limit: int | None) -> tuple[list[str], dict[str, Any]]:
    """טוען סימבולים מפלט rank_universe.py (schema v1). מחזיר רשימה לפי סדר הדירוג + מטא-דאטה."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    schema = data.get("schema")
    if schema != SCHEMA_RANK_V1:
        raise ValueError(
            f"קובץ דירוג לא תואם: צפוי schema={SCHEMA_RANK_V1!r}, התקבל {schema!r} ({path})"
        )
    top = data.get("top") or []
    if not top:
        raise ValueError(f"אין מפתח 'top' בקובץ הדירוג: {path}")
    symbols: list[str] = []
    weights: dict[str, float] = {}
    for row in top:
        sym = row.get("symbol")
        if not sym:
            continue
        sym = str(sym).upper()
        symbols.append(sym)
        w = row.get("weight")
        if w is not None:
            weights[sym] = float(w)
    if not symbols:
        raise ValueError(f"לא נמצאו סימבולים ב-top: {path}")
    if limit is not None and limit > 0:
        symbols = symbols[:limit]
        weights = {s: weights[s] for s in symbols if s in weights}
    meta = {
        "rank_json_path": str(path.resolve()),
        "rank_end_date": data.get("end_date"),
        "rank_top_k_file": data.get("top_k"),
        "rank_policy_file": data.get("policy_file"),
        "target_weights_from_rank": weights if weights else None,
    }
    return symbols, meta


def _warn_if_period_too_short_for_engine(period: str) -> None:
    p = period.strip().lower()
    if p in ("1y", "6mo", "3mo", "2mo", "1mo"):
        print(
            f"\n[אזהרה] המנוע דורש לפחות ~{_ENGINE_MIN_TRADING_DAYS} ימי מסחר. "
            f"עם --period {period!r} (ובמיוחד עם --end-date) לרוב יש פחות מזה — צפה לשגיאות "
            f"\"Need at least {_ENGINE_MIN_TRADING_DAYS} days\".\n"
            "המלצה: --period 2y או 3y.\n",
            file=sys.stderr,
        )


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Multi-Universe Backtest")
    ap.add_argument("--period", default="3y", help="Backtest period")
    ap.add_argument("--end-date", default=None, help="End date YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=None, help="Limit symbols (e.g. 10 for quick test)")
    ap.add_argument("--out", default=None, help="Save JSON path")
    ap.add_argument(
        "--profile",
        choices=("best_combo", "production"),
        default="best_combo",
        help="best_combo=legacy engine params | production=Stat+ML like run_backtest_with_ml",
    )
    ap.add_argument(
        "--no-ml",
        action="store_true",
        help="With --profile production: Stat only (no LSTM). Ignored for best_combo.",
    )
    ap.add_argument(
        "--disaster-threshold",
        type=float,
        default=0.80,
        help="production profile: P(down) block threshold (default 0.80)",
    )
    ap.add_argument("--low-vol-tilt", action="store_true", help="BacktestEngine low_vol_tilt (any profile)")
    ap.add_argument("--dual-momentum", action="store_true", help="BacktestEngine dual_momentum (any profile)")
    ap.add_argument(
        "--from-rank-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="יקום מסודר לפי פלט rank_universe.py (schema signalflow.universe_rank.v1); דורש קובץ תקין",
    )
    args = ap.parse_args()
    _warn_if_period_too_short_for_engine(args.period)

    rank_meta: dict[str, Any] | None = None
    if args.from_rank_json:
        if not args.from_rank_json.is_file():
            print(f"ERROR: קובץ דירוג לא נמצא: {args.from_rank_json}", file=sys.stderr)
            return 2
        try:
            symbols, rank_meta = _load_symbols_from_rank_json(args.from_rank_json, args.limit)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
    else:
        symbols = _load_universe()
        if args.limit:
            symbols = symbols[: args.limit]

    print("=" * 60)
    print("SignalFlow — Multi-Universe Backtest")
    print("=" * 60)
    profile_note = f"profile={args.profile}"
    if args.profile == "production" and args.no_ml:
        profile_note += " Stat-only"
    if args.low_vol_tilt:
        profile_note += " +low_vol_tilt"
    if args.dual_momentum:
        profile_note += " +dual_momentum"
    uni_note = f"Universe: {len(symbols)} symbols"
    if args.from_rank_json:
        uni_note += f" | source=rank_json ({args.from_rank_json.name})"
        if rank_meta and rank_meta.get("rank_end_date") and args.end_date:
            if str(rank_meta["rank_end_date"]) != str(args.end_date):
                print(
                    f"  [אזהרה] תאריך קצה בבקטסט ({args.end_date}) שונה מתאריך בקובץ הדירוג ({rank_meta['rank_end_date']})"
                )
    print(
        f"{uni_note} | Period: {args.period} | {profile_note}"
        + (f" | End: {args.end_date}" if args.end_date else "")
    )

    if args.profile == "best_combo":
        engine_kw = {
            "horizon": "daily",
            "use_ml": False,
            "mean_rev_mult": 2.0,
            "atr_stop_mult": 2.0,
            "vol_target_ann": 0.15,
            "commission_bps": 5,
            "slippage_bps": 3,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
        }
    else:
        engine_kw = {
            "horizon": "daily",
            "use_ml": not args.no_ml,
            "ml_threshold": 0.6,
            "ml_negative_filter": True,
            "ml_disaster_threshold": args.disaster_threshold,
            "mean_rev_mult": 1.0,
            "atr_stop_mult": 0.0,
            "vol_target_ann": None,
            "commission_bps": 5,
            "slippage_bps": 3,
            "low_vol_tilt": args.low_vol_tilt,
            "dual_momentum": args.dual_momentum,
        }

    results = []
    for sym in symbols:
        try:
            eng = BacktestEngine(**{**engine_kw, "symbol": sym})
            r = eng.run(period=args.period, end_date=args.end_date)
            results.append({"symbol": sym, "sharpe": r.sharpe_ratio, "return": r.total_return, "dd": r.max_drawdown, "trades": r.n_trades})
            print(f"  {sym}: Sharpe={r.sharpe_ratio:.3f} Return={r.total_return:.1%} DD={r.max_drawdown:.1%}")
        except Exception as e:
            print(f"  {sym}: ERROR {e}")
            results.append({"symbol": sym, "error": str(e)})

    ok = [x for x in results if "error" not in x]
    if ok:
        ret_avg = sum(x["return"] for x in ok) / len(ok)
        sharpe_avg = sum(x["sharpe"] for x in ok) / len(ok)
        dd_avg = sum(x["dd"] for x in ok) / len(ok)
        print(f"\n--- Aggregate ({len(ok)} symbols) ---")
        print(f"Avg Return: {ret_avg:.1%} | Avg Sharpe: {sharpe_avg:.3f} | Avg DD: {dd_avg:.1%}")

    payload: dict[str, Any] = {
        "results": results,
        "period": args.period,
        "end_date": args.end_date,
        "profile": args.profile,
        "no_ml": args.no_ml,
        "disaster_threshold": args.disaster_threshold if args.profile == "production" else None,
        "low_vol_tilt": args.low_vol_tilt,
        "dual_momentum": args.dual_momentum,
        "run_at": _utc_now_iso_z(),
        "universe_source": "rank_json" if args.from_rank_json else "symbols_yaml",
    }
    if rank_meta:
        payload["rank_meta"] = rank_meta
    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = Path(__file__).parent.parent / "run_outputs" / "research_runs"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug_end = (args.end_date or "latest").replace(":", "-")
        ranked_tag = "ranked_" if args.from_rank_json else ""
        out_path = out_dir / f"multi_{ranked_tag}{args.profile}_{args.period}_{slug_end}_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved: {out_path}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
