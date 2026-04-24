#!/usr/bin/env python
"""
סימולציית תיק: תשואות יומיות מהמנוע (כמו run_multi_universe) + ריענון Top‑N לפי פאנל.

- כל סימבול: BacktestEngine.run → daily_returns (סדרה עם תאריך).
- בכל יום ריענון (ברירת מחדל: יום שישי שמופיע בפאנל): בוחרים Top‑N לפי rank_in_universe מתוך שורות הפאנל באותו as_of_date.
- משקל שווה בין הנבחרים; עלות מחזור = חצי מ־sum(|Δw|) × round_trip (עמלה+סליפג’ כמו במנוע).

דוגמה:
  python scripts/simulate_ranked_portfolio.py \\
    --panel run_outputs/universe_panel/runs/panel_2023-01-03_2026-04-21_20260423_113533/panel.parquet \\
    --period 3y --end-date 2026-04-21 --top-n 5 --profile best_combo

תיעוד: docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.engine import BacktestEngine


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _engine_kw(
    profile: str,
    no_ml: bool,
    disaster_threshold: float,
    low_vol_tilt: bool,
    dual_momentum: bool,
) -> dict[str, Any]:
    if profile == "best_combo":
        return {
            "horizon": "daily",
            "use_ml": False,
            "mean_rev_mult": 2.0,
            "atr_stop_mult": 2.0,
            "vol_target_ann": 0.15,
            "commission_bps": 5,
            "slippage_bps": 3,
            "low_vol_tilt": low_vol_tilt,
            "dual_momentum": dual_momentum,
        }
    return {
        "horizon": "daily",
        "use_ml": not no_ml,
        "ml_threshold": 0.6,
        "ml_negative_filter": True,
        "ml_disaster_threshold": disaster_threshold,
        "mean_rev_mult": 1.0,
        "atr_stop_mult": 0.0,
        "vol_target_ann": None,
        "commission_bps": 5,
        "slippage_bps": 3,
        "low_vol_tilt": low_vol_tilt,
        "dual_momentum": dual_momentum,
    }


def _round_trip_frac(commission_bps: float, slippage_bps: float) -> float:
    return 2.0 * (commission_bps + slippage_bps) / 10_000.0


def _date_key(x: Any) -> str:
    """מפתח ייחודי לתאריך — נמנע כשל membership בין numpy.datetime64 ל-pandas.Timestamp."""
    return pd.Timestamp(x).strftime("%Y-%m-%d")


def _pick_top_symbols(panel_day: pd.DataFrame, top_n: int, allowed: set[str]) -> list[str]:
    sub = panel_day.loc[panel_day["eligible"].astype(bool)].copy()
    if sub.empty or sub["rank_in_universe"].notna().sum() == 0:
        return []
    sub = sub.sort_values("rank_in_universe")
    out: list[str] = []
    for sym in sub["symbol"].astype(str).str.upper():
        if sym in allowed and sym not in out:
            out.append(sym)
        if len(out) >= top_n:
            break
    return out


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description="Ranked portfolio simulation (panel + BacktestEngine)")
    ap.add_argument("--panel", type=Path, required=True, help="נתיב ל-panel.parquet")
    ap.add_argument("--period", default="3y", help="תקופת מנוע (כמו run_multi_universe)")
    ap.add_argument("--end-date", default=None, help="YYYY-MM-DD")
    ap.add_argument("--top-n", type=int, default=5, help="כמה מניות בכל ריענון")
    ap.add_argument(
        "--rebalance",
        choices=("weekly_friday", "daily"),
        default="weekly_friday",
        help="weekly_friday=רק תאריכי שישי מהפאנל | daily=כל יום מסחר בפאנל",
    )
    ap.add_argument("--profile", choices=("best_combo", "production"), default="best_combo")
    ap.add_argument("--no-ml", action="store_true")
    ap.add_argument("--disaster-threshold", type=float, default=0.80)
    ap.add_argument("--low-vol-tilt", action="store_true")
    ap.add_argument("--dual-momentum", action="store_true")
    ap.add_argument("--out", type=Path, default=None, help="JSON פלט")
    args = ap.parse_args()

    if not args.panel.is_file():
        print(f"ERROR: panel not found: {args.panel}", file=sys.stderr)
        return 2

    panel = pd.read_parquet(args.panel)
    panel["as_of_date"] = pd.to_datetime(panel["as_of_date"]).dt.normalize()
    panel["_date_key"] = panel["as_of_date"].dt.strftime("%Y-%m-%d")

    symbols = sorted(panel["symbol"].astype(str).str.upper().unique().tolist())
    engine_kw = _engine_kw(
        args.profile, args.no_ml, args.disaster_threshold, args.low_vol_tilt, args.dual_momentum
    )
    rt = _round_trip_frac(engine_kw["commission_bps"], engine_kw["slippage_bps"])

    print("=" * 60)
    print("SignalFlow — Ranked portfolio simulation")
    print("=" * 60)
    print(f"Panel: {args.panel.name} | symbols={len(symbols)} | top_n={args.top_n} | rebalance={args.rebalance}")
    print(f"Engine: {args.profile} | period={args.period} | end_date={args.end_date}")

    ret_map: dict[str, pd.Series] = {}
    failed: list[str] = []
    for sym in symbols:
        try:
            eng = BacktestEngine(**{**engine_kw, "symbol": sym})
            r = eng.run(period=args.period, end_date=args.end_date)
            if r.daily_returns is None or r.daily_returns.empty:
                failed.append(sym)
                continue
            s = r.daily_returns.copy()
            s.index = pd.to_datetime(s.index).normalize()
            ret_map[sym] = s
            print(f"  OK {sym}: days={len(s)}")
        except Exception as e:
            print(f"  FAIL {sym}: {e}")
            failed.append(sym)

    if len(ret_map) < 2:
        print("ERROR: need at least 2 symbols with daily_returns", file=sys.stderr)
        return 1

    master = pd.DatetimeIndex(sorted(set().union(*[set(s.index) for s in ret_map.values()])))
    master = master.sort_values()
    ret_df = pd.DataFrame(index=master, columns=sorted(ret_map.keys()), dtype=float)
    for sym, s in ret_map.items():
        ret_df[sym] = s.reindex(master).fillna(0.0)

    unique_days = np.sort(panel["as_of_date"].unique())
    if args.rebalance == "daily":
        rebalance_day_keys = {_date_key(d) for d in unique_days}
    else:
        rebalance_day_keys = {
            _date_key(d) for d in unique_days if pd.Timestamp(d).weekday() == 4
        }

    current_w = {sym: 0.0 for sym in ret_df.columns}
    port_ret: list[float] = []
    port_idx: list[pd.Timestamp] = []
    schedule: list[dict[str, Any]] = []

    for t in master:
        r_day = sum(current_w[sym] * float(ret_df.loc[t, sym]) for sym in ret_df.columns)
        t_key = _date_key(t)

        if t_key in rebalance_day_keys:
            day_panel = panel[panel["_date_key"] == t_key]
            allowed = set(ret_df.columns)
            top_syms = _pick_top_symbols(day_panel, args.top_n, allowed)
            new_w = {sym: 0.0 for sym in ret_df.columns}
            if top_syms:
                w = 1.0 / len(top_syms)
                for sym in top_syms:
                    if sym in new_w:
                        new_w[sym] = w
            turnover = 0.5 * sum(abs(new_w[sym] - current_w[sym]) for sym in ret_df.columns)
            cost = turnover * rt
            r_day -= cost
            schedule.append(
                {
                    "date": str(t.date()),
                    "holdings": sorted([s for s, wv in new_w.items() if wv > 0]),
                    "turnover": float(turnover),
                    "cost_frac": float(cost),
                }
            )
            current_w = new_w

        port_ret.append(r_day)
        port_idx.append(t)

    ser = pd.Series(port_ret, index=pd.DatetimeIndex(port_idx))
    sharpe = float(ser.mean() / ser.std() * np.sqrt(252)) if ser.std() > 1e-12 else 0.0
    eq = (1 + ser).cumprod()
    peak = eq.cummax()
    dd = float(((eq - peak) / peak).min()) if len(eq) else 0.0
    total_ret = float((1 + ser).prod() - 1)

    print("\n--- Portfolio ---")
    print(f"Sharpe ~ {sharpe:.3f} | Return ~ {total_ret:.1%} | MaxDD ~ {dd:.1%} | days={len(ser)}")
    if len(schedule) == 0:
        print(
            "[אזהרה] לא בוצע אף ריענון — בדוק התאמת תאריכים (תוקן בסקריפט: מפתח תאריך YYYY-MM-DD). "
            "הרץ שוב את הסימולציה.",
            file=sys.stderr,
        )

    payload: dict[str, Any] = {
        "run_at": _utc_now_iso_z(),
        "panel": str(args.panel.resolve()),
        "rebalance": args.rebalance,
        "top_n": args.top_n,
        "profile": args.profile,
        "period": args.period,
        "end_date": args.end_date,
        "engine_failed_symbols": failed,
        "n_rebalances": len(schedule),
        "portfolio": {
            "sharpe_ratio": sharpe,
            "total_return": total_ret,
            "max_drawdown": dd,
            "n_days": int(len(ser)),
        },
        "rebalance_schedule_sample": schedule[:8] + (["..."] if len(schedule) > 8 else []),
    }

    out_path = args.out
    if out_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = (
            root / "run_outputs" / "research_runs" / f"ranked_portfolio_{args.profile}_{args.top_n}_{ts}.json"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
