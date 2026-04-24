#!/usr/bin/env python
"""
SignalFlow — פאנל יקום יומי (as-of) + צינור 6 שלבים במחזור אחד.

שלב 0: חוזה נתונים (DATA_CONTRACT) + מטא (מדיניות, גרסה).
שלב 1: איסוף OHLCV (Yahoo) → מטמון תחת run_outputs/universe_panel/cache/.
שלב 2–3: בניית פאנל ארוך + פיצ'רים מיושרים ל־rank_universe.py (אותם חלונות ומשקלים).
שלב 4: דירוג חתכי יומי, decile, in_top_k, קטגוריות ליום הקצה.
שלב 5: ייצוא snapshot דירוג (signalflow.universe_rank.v1) + רשימת סימבולים לבקטסט.
שלב 6: אזהרות הטיות (survivorship וכו') + קובץ warnings.

דוגמה:
  python scripts/build_universe_panel.py --apply --start-date 2025-01-02 --end-date 2026-04-21 --limit 15
  python scripts/build_universe_panel.py --apply --start-date 2023-01-01 --end-date 2026-04-21

תיעוד: docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.fetchers.yahoo_finance import fetch_yahoo

try:
    import yaml
except ImportError:
    yaml = None

SCHEMA_PANEL_V1 = "signalflow.universe_panel.v1"
SCHEMA_RANK_V1 = "signalflow.universe_rank.v1"

DATA_CONTRACT: dict[str, Any] = {
    "version": 1,
    "knowledge_cutoff": (
        "כל שורה עם as_of_date=t משתמשת רק בנתוני מחיר/נפח עם תאריך <= t "
        "(סגירה יומית). אין שימוש בערכי עתיד."
    ),
    "price_field": "Adj Close אם קיים אחרת Close — כמו fetch_yahoo / rank_universe.",
    "momentum_definition": "close(t) / close(t-window_trading_days) - 1 (ימי מסחר).",
    "liquidity": "ממוצע נפח דולרי 20 יום סוף חלון עד t.",
    "volatility": "סטיית תקן תשואות יומיות 60 יום * sqrt(252); חסרים ממולאים במדיאנה החתכית באותו יום.",
    "execution_research_note": (
        "הפאנל מתאר מה היה ידוע לפי סגירות; לא מדמה מחיר כניסה t+1. "
        "להקשחת בקטסט ראו מדיניות נפרדת במנוע."
    ),
    "aligned_scripts": ["scripts/rank_universe.py"],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_universe() -> list[str]:
    cfg = _repo_root() / "config" / "symbols.yaml"
    if not cfg.exists():
        return ["AAPL", "MSFT", "GOOGL", "SPY"]
    if yaml is None:
        return ["AAPL", "MSFT", "GOOGL", "SPY"]
    with open(cfg, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(
        data.get(
            "universe",
            data.get("primary", ["AAPL", "MSFT", "GOOGL", "SPY"]),
        )
    )


def _load_policy(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise SystemExit("נדרש PyYAML: pip install pyyaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _policy_hash(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest()[:16]


def _git_sha() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()[:40]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _allocate_weights(rows: list[dict], allocation: str, max_w: float) -> None:
    n = len(rows)
    if n == 0:
        return
    if allocation == "equal":
        base = 1.0 / n
        for r in rows:
            r["weight"] = min(base, max_w)
    elif allocation == "inverse_volatility":
        inv = []
        for r in rows:
            v = r.get("volatility_ann_60d") or 0.0
            inv.append(1.0 / v if v > 1e-8 else 0.0)
        s = sum(inv)
        if s <= 0:
            _allocate_weights(rows, "equal", max_w)
            return
        for r, w in zip(rows, inv):
            r["weight"] = min(w / s, max_w)
        tot = sum(r["weight"] for r in rows)
        if tot > 0 and tot < 0.999:
            for r in rows:
                r["weight"] = r["weight"] / tot
    else:
        _allocate_weights(rows, "equal", max_w)


def _normalize_index_daily(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    idx = pd.to_datetime(out.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    out.index = idx.normalize()
    return out.sort_index()


def _fetch_bars(symbol: str, start: pd.Timestamp, end_inclusive: pd.Timestamp) -> pd.DataFrame:
    end_fetch = (end_inclusive + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    df = fetch_yahoo(
        symbol,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end_fetch,
        min_rows=10,
    )
    return _normalize_index_daily(df)


def _cache_path(symbol: str) -> Path:
    return _repo_root() / "run_outputs" / "universe_panel" / "cache" / "bars_v1" / f"{symbol.upper()}.parquet"


def _load_or_fetch_bars(
    symbol: str,
    need_start: pd.Timestamp,
    need_end: pd.Timestamp,
    refresh: bool,
) -> Optional[pd.DataFrame]:
    path = _cache_path(symbol)
    if not refresh and path.is_file():
        try:
            df = pd.read_parquet(path)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df["date"])
                df = df.drop(columns=["date"], errors="ignore")
            df = _normalize_index_daily(df)
            if len(df) >= 30 and df.index.min() <= need_start and df.index.max() >= need_end:
                return df
        except Exception:
            pass
    try:
        df = _fetch_bars(symbol, need_start, need_end)
    except Exception:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path)
    except Exception:
        pass
    return df


def _per_symbol_features(
    df: pd.DataFrame,
    symbol: str,
    window: int,
    min_liq: float,
) -> pd.DataFrame:
    close = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
    vol = df["Volume"].astype(float)
    dv = (close * vol).astype(float)
    rets = close.pct_change()

    out = pd.DataFrame(
        {
            "symbol": symbol,
            "close": close.astype(float),
            "volume": vol,
            "liquidity_20d_avg": dv.rolling(20, min_periods=20).mean(),
            "momentum_window_return": close / close.shift(window) - 1.0,
            "volatility_ann_60d": rets.rolling(60, min_periods=60).std() * np.sqrt(252),
        }
    )
    out.index.name = "as_of_date"
    out = out.reset_index()

    out["eligible_liquidity"] = out["liquidity_20d_avg"] >= min_liq
    out["eligible_momentum"] = out["momentum_window_return"].notna()
    out["eligible"] = out["eligible_liquidity"] & out["eligible_momentum"]
    return out


def _cross_section_scores(day: pd.DataFrame, w_m: float, w_l: float, w_v: float) -> pd.DataFrame:
    day = day.copy()
    for c in ("r_mom", "r_liq", "r_vol", "score", "rank_in_universe", "decile", "score_pctile_in_universe"):
        day[c] = np.nan

    sub = day.loc[day["eligible"]].copy()
    if sub.empty:
        return day

    # מיושר ל-rank_universe: ערך גבוה יותר (מומנטום / נזילות) → אחוזון גבוה יותר
    sub["r_mom"] = sub["momentum_window_return"].rank(pct=True, ascending=True)
    sub["r_liq"] = sub["liquidity_20d_avg"].rank(pct=True, ascending=True)
    vcol = sub["volatility_ann_60d"].fillna(sub["volatility_ann_60d"].median())
    sub["r_vol"] = 1.0 - vcol.rank(pct=True, ascending=True)
    sub["score"] = w_m * sub["r_mom"] + w_l * sub["r_liq"] + w_v * sub["r_vol"]
    sub = sub.sort_values("score", ascending=False)
    sub["rank_in_universe"] = np.arange(1, len(sub) + 1, dtype=float)
    sub["score_pctile_in_universe"] = sub["score"].rank(pct=True, ascending=True)
    sub["decile"] = np.ceil(sub["score_pctile_in_universe"] * 10).clip(1, 10).astype(int)

    idx = sub.set_index("symbol")
    for col in ("r_mom", "r_liq", "r_vol", "score", "rank_in_universe", "decile", "score_pctile_in_universe"):
        day[col] = day["symbol"].map(idx[col])

    return day


def step0_write_contract(run_dir: Path, policy_path: Path, extra_meta: dict[str, Any]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    p = run_dir / "DATA_CONTRACT.json"
    payload = {"schema": SCHEMA_PANEL_V1 + ".contract", **DATA_CONTRACT, **extra_meta}
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def step6_warnings_path(run_dir: Path, ack: bool) -> Path:
    lines = [
        "שלב 6 — אזהרות מתודולוגיות",
        "",
        "- Survivorship: היקום מ-config/symbols.yaml הוא לרוב רשימה נוכחית — אין כאן מניות delisted היסטוריות.",
        "- הרכב מדד: לא נבנה כאן S&P point-in-time constituents.",
        "- נתונים: Yahoo Finance; עיכובים/תיקונים אינם מדמים PiT מוסדי מלא.",
        "- שינויי מדיניות: אם hot_universe_policy.yaml השתנה — יש לייצר פאנל חדש (policy_hash במטא).",
        "",
        f"survivorship_acknowledged_by_flag: {bool(ack)}",
    ]
    out = run_dir / "WARNINGS.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _build_rank_snapshot_from_day(
    day_df: pd.DataFrame,
    policy: dict[str, Any],
    end_date_str: str,
    policy_path: Path,
) -> dict[str, Any]:
    rank_cfg = policy.get("ranking", {})
    window = int(rank_cfg.get("momentum_window_trading_days", 63))
    weights = rank_cfg.get("weights", {})
    w_m = float(weights.get("momentum", 0.7))
    w_l = float(weights.get("liquidity", 0.2))
    w_v = float(weights.get("low_volatility", 0.1))
    s_w = w_m + w_l + w_v
    if s_w > 0:
        w_m, w_l, w_v = w_m / s_w, w_l / s_w, w_v / s_w

    port = policy.get("portfolio", {})
    top_k = int(port.get("top_k", 10))
    max_w = float(port.get("max_weight_per_symbol", 0.2))
    allocation = str(port.get("allocation", "equal"))
    ref_syms = [str(s).upper() for s in policy.get("reference_symbols", ["AAPL"])]

    elig = day_df[day_df["eligible"]].copy()
    if elig.empty:
        return {
            "schema": SCHEMA_RANK_V1,
            "end_date": end_date_str,
            "policy_file": str(policy_path),
            "error": "no_eligible_symbols",
            "top": [],
        }

    top = elig.sort_values("rank_in_universe").head(top_k)
    records: list[dict[str, Any]] = []
    for _, row in top.iterrows():
        sym = str(row["symbol"]).upper()
        rnk = int(row["rank_in_universe"]) if pd.notna(row["rank_in_universe"]) else None
        records.append(
            {
                "symbol": sym,
                "in_top_k": True,
                "skip": False,
                "momentum_window_return": float(row["momentum_window_return"]),
                "liquidity_20d_avg": float(row["liquidity_20d_avg"]),
                "volatility_ann_60d": float(row["volatility_ann_60d"])
                if pd.notna(row["volatility_ann_60d"])
                else None,
                "r_mom": float(row["r_mom"]) if pd.notna(row["r_mom"]) else None,
                "r_liq": float(row["r_liq"]) if pd.notna(row["r_liq"]) else None,
                "r_vol": float(row["r_vol"]) if pd.notna(row["r_vol"]) else None,
                "score": float(row["score"]) if pd.notna(row["score"]) else None,
                "rank": rnk,
            }
        )

    top_set = {r["symbol"] for r in records}
    ref_out: list[dict[str, Any]] = []
    for ref in ref_syms:
        if ref not in top_set:
            hit = elig[elig["symbol"] == ref]
            if not hit.empty:
                row = hit.iloc[0]
                rnk = int(row["rank_in_universe"]) if pd.notna(row["rank_in_universe"]) else None
                ref_out.append(
                    {
                        "symbol": ref,
                        "in_top_k": False,
                        "skip": False,
                        "momentum_window_return": float(row["momentum_window_return"]),
                        "liquidity_20d_avg": float(row["liquidity_20d_avg"]),
                        "volatility_ann_60d": float(row["volatility_ann_60d"])
                        if pd.notna(row["volatility_ann_60d"])
                        else None,
                        "r_mom": float(row["r_mom"]) if pd.notna(row["r_mom"]) else None,
                        "r_liq": float(row["r_liq"]) if pd.notna(row["r_liq"]) else None,
                        "r_vol": float(row["r_vol"]) if pd.notna(row["r_vol"]) else None,
                        "score": float(row["score"]) if pd.notna(row["score"]) else None,
                        "rank": rnk,
                    }
                )
            else:
                ref_out.append(
                    {"symbol": ref, "in_top_k": False, "note": "לא נכלל בדירוג (נתונים/נזילות/היסטוריה)"}
                )

    _allocate_weights(records, allocation, max_w)

    return {
        "schema": SCHEMA_RANK_V1,
        "end_date": end_date_str,
        "policy_file": str(policy_path),
        "momentum_window_trading_days": window,
        "weights": {"momentum": w_m, "liquidity": w_l, "low_volatility": w_v},
        "reference_symbols": ref_syms,
        "top_k": top_k,
        "allocation": allocation,
        "top": records,
        "reference_not_in_top": ref_out,
        "skipped": [],
        "universe_size_requested": int(day_df["symbol"].nunique()),
        "ranked_count": int(len(elig)),
        "source": "build_universe_panel.py snapshot (last as_of_date)",
    }


def main() -> int:
    root = _repo_root()
    ap = argparse.ArgumentParser(
        description="בניית פאנל יקום יומי + 6 שלבים (ראו DATA_CONTRACT בפלט)"
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="מבצע את הצינור (קריאות רשת, כתיבת קבצים). בלי דגל זה — עזרה בלבד.",
    )
    ap.add_argument("--policy", type=Path, default=root / "config" / "hot_universe_policy.yaml")
    ap.add_argument("--start-date", required=True, help="תאריך התחלה כלול (YYYY-MM-DD)")
    ap.add_argument("--end-date", required=True, help="תאריך קצה כלול (YYYY-MM-DD)")
    ap.add_argument("--symbols", default=None, help="רשימת סימבולים מופרדת בפסיקים (דורס symbols.yaml)")
    ap.add_argument("--limit", type=int, default=None, help="הגבלת מספר סימבולים מהיקום (בדיקה מהירה)")
    ap.add_argument(
        "--refresh-bars",
        action="store_true",
        help="מחייב איסוף מחדש מ-Yahoo (מתעלם ממטמון parquet)",
    )
    ap.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="תיקיית פלט; ברירת מחדל: run_outputs/universe_panel/runs/panel_<...>",
    )
    ap.add_argument(
        "--i-understand-survivorship",
        action="store_true",
        help="מסמן ב-WARNINGS שההטיה הוסברה (לא משנה נתונים)",
    )
    args = ap.parse_args()

    if not args.apply:
        ap.print_help()
        print(
            "\nהוסף --apply להרצה מלאה. דוגמה:\n"
            "  python scripts/build_universe_panel.py --apply "
            "--start-date 2025-01-02 --end-date 2026-04-21 --limit 10\n",
            file=sys.stderr,
        )
        return 0

    if yaml is None:
        print("ERROR: נדרש PyYAML", file=sys.stderr)
        return 1

    policy_path = args.policy
    if not policy_path.is_file():
        print(f"ERROR: קובץ מדיניות לא נמצא: {policy_path}", file=sys.stderr)
        return 1

    policy = _load_policy(policy_path)
    rank_cfg = policy.get("ranking", {})
    window = int(rank_cfg.get("momentum_window_trading_days", 63))
    weights = rank_cfg.get("weights", {})
    w_m = float(weights.get("momentum", 0.7))
    w_l = float(weights.get("liquidity", 0.2))
    w_v = float(weights.get("low_volatility", 0.1))
    s_w = w_m + w_l + w_v
    if s_w > 0:
        w_m, w_l, w_v = w_m / s_w, w_l / s_w, w_v / s_w

    liq_cfg = policy.get("liquidity", {})
    min_liq = float(liq_cfg.get("min_avg_dollar_volume_20d", 2_000_000))
    port = policy.get("portfolio", {})
    top_k = int(port.get("top_k", 10))

    start = pd.Timestamp(args.start_date).normalize()
    end = pd.Timestamp(args.end_date).normalize()
    if end < start:
        print("ERROR: end-date לפני start-date", file=sys.stderr)
        return 1

    need_start = start - pd.Timedelta(days=450)
    phash = _policy_hash(policy_path)
    run_id = _utc_run_id()
    run_dir = args.run_dir or (
        root / "run_outputs" / "universe_panel" / "runs" / f"panel_{start.date()}_{end.date()}_{run_id}"
    )

    # --- שלב 0 ---
    meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "policy_path": str(policy_path.resolve()),
        "policy_hash_sha256_16": phash,
        "git_sha": _git_sha(),
        "start_date": str(start.date()),
        "end_date": str(end.date()),
        "momentum_window_trading_days": window,
        "weights": {"momentum": w_m, "liquidity": w_l, "low_volatility": w_v},
        "min_avg_dollar_volume_20d": min_liq,
        "top_k": top_k,
    }
    step0_write_contract(run_dir, policy_path, {"meta": meta})
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.symbols:
        universe = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
    else:
        universe = [u.upper() for u in _load_universe()]
    if args.limit:
        universe = universe[: args.limit]

    # --- שלב 1: איסוף ---
    fetched_ok = 0
    frames: list[pd.DataFrame] = []
    failed: list[str] = []
    for sym in universe:
        df = _load_or_fetch_bars(sym, need_start, end, args.refresh_bars)
        if df is None or len(df) < window + 65:
            failed.append(sym)
            continue
        fetched_ok += 1
        frames.append(_per_symbol_features(df, sym, window, min_liq))

    if not frames:
        print("ERROR: אין מספיק נתונים לאף סימבול.", file=sys.stderr)
        return 1

    panel = pd.concat(frames, ignore_index=True)
    panel["as_of_date"] = pd.to_datetime(panel["as_of_date"]).dt.normalize()
    panel = panel[(panel["as_of_date"] >= start) & (panel["as_of_date"] <= end)]

    # --- שלב 2–4: דירוג חתכי לכל יום ---
    day_frames: list[pd.DataFrame] = []
    for d, day in panel.groupby("as_of_date", sort=True):
        day_scored = _cross_section_scores(day, w_m, w_l, w_v)
        day_scored["in_top_k"] = False
        ok = day_scored["eligible"] & day_scored["rank_in_universe"].notna()
        if ok.any():
            rk = day_scored.loc[ok, "rank_in_universe"]
            day_scored.loc[ok & (rk <= top_k), "in_top_k"] = True
        day_frames.append(day_scored)

    panel_out = pd.concat(day_frames, ignore_index=True)
    panel_out.attrs.clear()

    if panel_out.empty:
        print("ERROR: הפאנל ריק אחרי סינון תאריכים (בדוק start/end ונתונים).", file=sys.stderr)
        return 1

    actual_end = pd.Timestamp(panel_out["as_of_date"].max()).normalize()
    last_day = panel_out[panel_out["as_of_date"] == actual_end].copy()
    end_date_for_snapshot = str(actual_end.date())

    # --- כתיבת פאנל ---
    parquet_path = run_dir / "panel.parquet"
    csv_fallback = run_dir / "panel.csv.gz"
    try:
        panel_out.to_parquet(parquet_path, index=False)
        written_panel = parquet_path
    except Exception as e:
        panel_out.to_csv(csv_fallback, index=False, compression="gzip")
        written_panel = csv_fallback
        (run_dir / "PARQUET_FALLBACK.txt").write_text(
            f"pyarrow/fastparquet not available or error: {e}\nWrote CSV gzip instead.\n",
            encoding="utf-8",
        )

    # קטגוריות ליום הקצה (יום המסחר האחרון בפאלט)
    categories: dict[str, Any] = {
        "as_of_date": end_date_for_snapshot,
        "by_decile": {},
        "in_top_k": [],
    }
    if not last_day.empty:
        for dec in range(1, 11):
            syms = last_day.loc[last_day["decile"] == dec, "symbol"].astype(str).tolist()
            categories["by_decile"][str(dec)] = sorted(set(syms))
        categories["in_top_k"] = sorted(
            last_day.loc[last_day["in_top_k"], "symbol"].astype(str).tolist()
        )
    (run_dir / "categories_end.json").write_text(
        json.dumps(categories, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ingest_report = {
        "universe_requested": universe,
        "fetch_ok_count": fetched_ok,
        "fetch_failed": failed,
        "panel_rows": int(len(panel_out)),
        "panel_path": str(written_panel.resolve()),
    }
    (run_dir / "ingest_report.json").write_text(
        json.dumps(ingest_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- שלב 5: snapshot דירוג ---
    snap = _build_rank_snapshot_from_day(last_day, policy, end_date_for_snapshot, policy_path)
    rank_path = run_dir / f"snapshot_rank_{end_date_for_snapshot}.json"
    rank_path.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")

    symbols_txt = run_dir / "symbols_top_k.txt"
    syms_top = [r["symbol"] for r in snap.get("top", []) if r.get("symbol")]
    symbols_txt.write_text("\n".join(syms_top) + ("\n" if syms_top else ""), encoding="utf-8")

    readme = run_dir / "NEXT_STEPS.txt"
    readme.write_text(
        "בקטסט רב-סימבולים לפי snapshot הדירוג:\n"
        f"  python scripts/run_multi_universe.py --from-rank-json {rank_path.as_posix()} "
        f"--period 3y --end-date {end_date_for_snapshot}\n\n"
        f"פאנל מלא: {written_panel.name}\n"
        f"יום המסחר האחרון בפאנל: {end_date_for_snapshot}\n",
        encoding="utf-8",
    )

    # --- שלב 6 ---
    step6_warnings_path(run_dir, args.i_understand_survivorship)

    print(f"נשמרו קבצים תחת: {run_dir}")
    print(f"  פאנל: {written_panel.name}")
    print(f"  snapshot דירוג: {rank_path.name}")
    print(f"  Top-K symbols: {symbols_txt.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
