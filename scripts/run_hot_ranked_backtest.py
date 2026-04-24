#!/usr/bin/env python
"""
צינור: דירוג יקום (rank_universe) → בקטסט רב־סימבולים (run_multi_universe --from-rank-json).

לא משנה ברירות מחדל של סקריפטים אחרים; מפעיל רק כשמריצים מפורשות את הסקריפט.

תיעוד: docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md

דוגמה:
  python scripts/run_hot_ranked_backtest.py --end-date 2026-04-21 --profile best_combo --period 3y
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Hot universe: rank → multi backtest")
    ap.add_argument("--end-date", required=True, help="תאריך קצה לדירוג ולבקטסט (YYYY-MM-DD)")
    ap.add_argument("--policy", type=Path, default=ROOT / "config" / "hot_universe_policy.yaml")
    ap.add_argument("--profile", choices=("best_combo", "production"), default="best_combo")
    ap.add_argument(
        "--period",
        default="3y",
        help="תקופת בקטסט; לא להשתמש ב-1y עם --end-date (פחות מ-302 ימי מסחר). מומלץ 2y–3y",
    )
    ap.add_argument("--limit", type=int, default=None, help="חתוך את רשימת ה-top מהדירוג")
    ap.add_argument("--no-ml", action="store_true", help="עם production: Stat בלבד")
    ap.add_argument("--low-vol-tilt", action="store_true")
    ap.add_argument("--dual-momentum", action="store_true")
    ap.add_argument(
        "--disaster-threshold",
        type=float,
        default=0.80,
        help="עם --profile production: סף P(down) (ברירת 0.80)",
    )
    ap.add_argument(
        "--rank-out",
        type=Path,
        default=None,
        help="נתיב לשמירת JSON דירוג; ברירת מחדל: run_outputs/rankings/pipeline_<timestamp>.json",
    )
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rank_path = args.rank_out or (
        ROOT / "run_outputs" / "rankings" / f"pipeline_rank_{args.end_date}_{ts}.json"
    )
    rank_path.parent.mkdir(parents=True, exist_ok=True)

    r1 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "rank_universe.py"),
            "--apply-policy",
            "--policy",
            str(args.policy),
            "--end-date",
            args.end_date,
            "--out",
            str(rank_path),
        ],
        cwd=str(ROOT),
    )
    if r1.returncode != 0:
        return r1.returncode

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_multi_universe.py"),
        "--from-rank-json",
        str(rank_path),
        "--period",
        args.period,
        "--end-date",
        args.end_date,
        "--profile",
        args.profile,
    ]
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])
    if args.profile == "production" and args.no_ml:
        cmd.append("--no-ml")
    if args.low_vol_tilt:
        cmd.append("--low-vol-tilt")
    if args.dual_momentum:
        cmd.append("--dual-momentum")
    if args.profile == "production":
        cmd.extend(["--disaster-threshold", str(args.disaster_threshold)])

    r2 = subprocess.run(cmd, cwd=str(ROOT))
    return r2.returncode


if __name__ == "__main__":
    sys.exit(main())
