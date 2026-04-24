#!/usr/bin/env python
"""
דירוג חתך צולב ליקום — שלב 1 (חוזק יחסי + נזילות + העדפת תנודתיות נמוכה).

ברירת מחדל: לא מבצע קריאות רשת. יש להעביר --apply-policy.

תיעוד: docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md · config/hot_universe_policy.yaml

דוגמה:
  python scripts/rank_universe.py --apply-policy --end-date 2026-04-21
  # (פלט אוטומטי ל־run_outputs/rankings/ אם לא מועבר --out)
"""
from __future__ import annotations

import argparse
import json
import sys
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_universe() -> list[str]:
    cfg = _repo_root() / "config" / "symbols.yaml"
    if not cfg.exists():
        return ["AAPL", "MSFT", "GOOGL", "SPY"]
    with open(cfg, encoding="utf-8") as f:
        data = yaml.safe_load(f) if yaml else {}
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


def _fetch_daily(symbol: str, end_ts: pd.Timestamp) -> Optional[pd.DataFrame]:
    start = end_ts - pd.Timedelta(days=450)
    end_inclusive = (end_ts + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        df = fetch_yahoo(
            symbol,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end_inclusive,
            min_rows=10,
        )
        if df is None or len(df) < 30:
            return None
        return df.sort_index()
    except Exception:
        return None


def _metrics_for_symbol(
    symbol: str,
    end_ts: pd.Timestamp,
    window: int,
    min_liq: float,
) -> Optional[dict[str, Any]]:
    df = _fetch_daily(symbol, end_ts)
    if df is None:
        return None
    close = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
    vol = df["Volume"].astype(float)
    dv = (close * vol).dropna()
    if len(dv) < 20:
        return None
    liq = float(dv.tail(20).mean())
    if liq < min_liq:
        return {"symbol": symbol, "skip": True, "reason": "below_liquidity_floor", "liquidity_20d_avg": liq}

    rets = close.pct_change().dropna()
    vol_ann = float(rets.tail(60).std() * np.sqrt(252)) if len(rets) >= 20 else float("nan")

    if len(close) < window + 1:
        return {"symbol": symbol, "skip": True, "reason": "insufficient_history", "liquidity_20d_avg": liq}

    c0 = float(close.iloc[-(window + 1)])
    c1 = float(close.iloc[-1])
    if c0 <= 0:
        return None
    momentum = (c1 / c0) - 1.0

    return {
        "symbol": symbol,
        "skip": False,
        "momentum_window_return": momentum,
        "liquidity_20d_avg": liq,
        "volatility_ann_60d": vol_ann,
    }


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
        # Renormalize if caps hit — simple fallback
        tot = sum(r["weight"] for r in rows)
        if tot > 0 and tot < 0.999:
            for r in rows:
                r["weight"] = r["weight"] / tot
    else:
        _allocate_weights(rows, "equal", max_w)


def main() -> int:
    root = _repo_root()
    ap = argparse.ArgumentParser(description="דירוג יקום (שלב 1) — רק עם --apply-policy")
    ap.add_argument(
        "--apply-policy",
        action="store_true",
        help="מבצע דירוג וקריאות נתונים; בלי דגל זה הסקריפט אינו פועל",
    )
    ap.add_argument("--policy", type=Path, default=root / "config" / "hot_universe_policy.yaml")
    ap.add_argument("--end-date", default=None, help="תאריך קצה לשחזור (YYYY-MM-DD); ברירת מחדל: היום")
    ap.add_argument("--out", type=Path, default=None, help="שמירת JSON (נוצרת תיקייה אם חסרה)")
    ap.add_argument("--limit", type=int, default=None, help="הגבלת מספר סימבולים מהיקום (בדיקה מהירה)")
    ap.add_argument(
        "--symbols",
        default=None,
        help="רשימה מופרדת בפסיקים; דורס את היקום מ-symbols.yaml",
    )
    args = ap.parse_args()

    if not args.apply_policy:
        print(
            "rank_universe: לא בוצע דירוג (אין קריאות רשת).\n"
            "הוסף --apply-policy להרצה מלאה. עזרה: python scripts/rank_universe.py --help\n"
            "תיעוד: docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md"
        )
        return 0

    policy = _load_policy(args.policy)
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
    max_w = float(port.get("max_weight_per_symbol", 0.2))
    allocation = str(port.get("allocation", "equal"))

    ref_syms = [str(s).upper() for s in policy.get("reference_symbols", ["AAPL"])]

    if args.symbols:
        universe = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
    else:
        universe = [u.upper() for u in _load_universe()]
    if args.limit:
        universe = universe[: args.limit]

    end_ts = pd.Timestamp(args.end_date) if args.end_date else pd.Timestamp.today().normalize()

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for sym in universe:
        m = _metrics_for_symbol(sym, end_ts, window, min_liq)
        if m is None:
            skipped.append({"symbol": sym, "reason": "fetch_or_data"})
            continue
        if m.get("skip"):
            skipped.append(m)
            continue
        rows.append(m)

    if not rows:
        print("אין מספיק נתונים לדירוג.")
        return 1

    df = pd.DataFrame(rows)
    # דירוג חתכי: מומנטום גבוה = ציון גבוה; נזילות גבוהה = ציון גבוה
    # pct=True עם ascending=True: ערך גדול יותר → אחוזון גבוה יותר (1 = הכי טוב בחתך)
    df["r_mom"] = df["momentum_window_return"].rank(pct=True, ascending=True)
    df["r_liq"] = df["liquidity_20d_avg"].rank(pct=True, ascending=True)
    # תנודתיות נמוכה = ציון גבוה (מילוי חסרים לבינוני כדי לא לשבור דירוג)
    vcol = df["volatility_ann_60d"].fillna(df["volatility_ann_60d"].median())
    df["r_vol"] = 1.0 - vcol.rank(pct=True, ascending=True)
    df["score"] = w_m * df["r_mom"] + w_l * df["r_liq"] + w_v * df["r_vol"]

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)

    top = df.head(top_k).to_dict("records")
    for r in top:
        r["in_top_k"] = True

    # סימבולי ייחוס שלא בטופ
    ref_out: list[dict[str, Any]] = []
    top_set = {r["symbol"] for r in top}
    for ref in ref_syms:
        if ref not in top_set:
            hit = df[df["symbol"] == ref]
            if not hit.empty:
                rec = hit.iloc[0].to_dict()
                rec["in_top_k"] = False
                ref_out.append(rec)
            else:
                ref_out.append({"symbol": ref, "in_top_k": False, "note": "לא נכלל בדירוג (נתונים/נזילות/היסטוריה)"})

    _allocate_weights(top, allocation, max_w)

    payload = {
        "schema": "signalflow.universe_rank.v1",
        "end_date": str(end_ts.date()),
        "policy_file": str(args.policy),
        "momentum_window_trading_days": window,
        "weights": {"momentum": w_m, "liquidity": w_l, "low_volatility": w_v},
        "reference_symbols": ref_syms,
        "top_k": top_k,
        "allocation": allocation,
        "top": top,
        "reference_not_in_top": ref_out,
        "skipped": skipped,
        "universe_size_requested": len(universe),
        "ranked_count": len(df),
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    out_path = args.out
    if out_path is None:
        ts = pd.Timestamp.utcnow().strftime("%H%M%S")
        out_path = root / "run_outputs" / "rankings" / f"universe_rank_{str(end_ts.date())}_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"נשמר: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
