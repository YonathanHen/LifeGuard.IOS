#!/usr/bin/env python
"""
Run isolated research backtests from config/research_run_matrix.yaml.

Each run uses explicit CLI flags only — no change to engine defaults.
Outputs:
  - run_backtest_with_ml: labels in run_outputs/backtest_runs.json (+ mirror storage/)
  - run_multi_universe / run_enhancement_ab: JSON under run_outputs/research_runs/

Usage:
  python scripts/run_research_suite.py --list
  python scripts/run_research_suite.py --dry-run
  python scripts/run_research_suite.py --group single
  python scripts/run_research_suite.py --quick
  python scripts/run_research_suite.py --only s01_bwml_baseline,m02_multi_best_combo_lowvol
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_matrix(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _format_args(args_list: list, ctx: dict) -> list[str]:
    out = []
    for a in args_list:
        if isinstance(a, str):
            out.append(a.format(**ctx))
        else:
            out.append(str(a))
    return out


def main() -> int:
    root = _repo_root()
    default_matrix = root / "config" / "research_run_matrix.yaml"

    ap = argparse.ArgumentParser(description="Run SignalFlow research suite (isolated outputs)")
    ap.add_argument("--matrix", type=Path, default=default_matrix, help="YAML matrix path")
    ap.add_argument("--list", action="store_true", help="Print runs and exit")
    ap.add_argument("--dry-run", action="store_true", help="Print commands only")
    ap.add_argument("--quick", action="store_true", help="Shorter period + smaller universe (see YAML defaults)")
    ap.add_argument("--group", choices=("all", "single", "multi", "ab"), default="all", help="Filter runs by group")
    ap.add_argument("--only", type=str, default=None, help="Comma-separated run ids")
    ap.add_argument("--symbol", type=str, default=None, help="Override default symbol")
    ap.add_argument("--stop-on-fail", action="store_true", help="Stop after first non-zero exit")
    args = ap.parse_args()

    data = _load_matrix(args.matrix)
    defaults = data.get("defaults") or {}
    runs = data.get("runs") or []

    period = (defaults.get("period_quick") if args.quick else defaults.get("period_full")) or "3y"
    multi_limit = defaults.get("multi_limit_quick" if args.quick else "multi_limit_full") or 10
    symbol = args.symbol or defaults.get("symbol") or "AAPL"
    out_dir = root / "run_outputs" / "research_runs"
    out_dir.mkdir(parents=True, exist_ok=True)

    period_slug = period.replace(" ", "")

    ctx = {
        "period": period,
        "period_slug": period_slug,
        "symbol": symbol,
        "multi_limit": str(multi_limit),
        "out_dir": str(out_dir).replace("\\", "/"),
    }

    only_set = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None

    filtered = []
    for r in runs:
        rid = r.get("id")
        grp = r.get("group", "")
        if args.group != "all" and grp != args.group:
            continue
        if only_set is not None and rid not in only_set:
            continue
        filtered.append(r)

    if args.list:
        print(f"Matrix: {args.matrix}")
        print(f"Context: period={period} symbol={symbol} multi_limit={multi_limit} out_dir={out_dir}\n")
        for r in filtered:
            print(f"  [{r.get('group'):6}] {r.get('id')}: {r.get('title', '')}")
        print(f"\nTotal: {len(filtered)} run(s)")
        return 0

    manifest = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "matrix": str(args.matrix),
        "quick": args.quick,
        "group": args.group,
        "only": args.only,
        "context": ctx,
        "runs": [],
    }

    print("=" * 70)
    print("SignalFlow — research suite")
    print("=" * 70)
    print(f"Runs: {len(filtered)} | period={period} | symbol={symbol} | multi_limit={multi_limit}")
    print(f"Out dir: {out_dir}\n")

    failures = []
    for i, r in enumerate(filtered, 1):
        rid = r["id"]
        script = r["script"]
        argv = _format_args(r.get("args") or [], ctx)
        cmd = [sys.executable, str(root / script)] + argv

        print(f"--- [{i}/{len(filtered)}] {rid} ---")
        print(" ", " ".join(cmd))
        engine_summary = (r.get("engine") or "").strip()
        if args.dry_run:
            manifest["runs"].append(
                {
                    "id": rid,
                    "engine": engine_summary,
                    "cmd": cmd,
                    "exit_code": None,
                    "skipped": True,
                }
            )
            continue

        proc = subprocess.run(cmd, cwd=str(root))
        manifest["runs"].append(
            {
                "id": rid,
                "engine": engine_summary,
                "cmd": cmd,
                "exit_code": proc.returncode,
            }
        )
        if proc.returncode != 0:
            failures.append(rid)
            if args.stop_on_fail:
                print(f"\nStopped on failure: {rid}")
                break

    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["failures"] = failures
    manifest["documentation_requirement"] = (
        "לאחר הרצה: עדכן docs/RESEARCH_DECISIONS_LOG.md — לכל ניסוי חובה "
        "אלגוריתמים/דגלים (או העתק משדה engine במניפסט), תוצאות עיקריות, מסקנות, קבצי גולם."
    )

    if not args.dry_run:
        man_path = out_dir / f"_suite_manifest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(man_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\nManifest: {man_path}")
        print("\nתיעוד (חובה): docs/RESEARCH_DECISIONS_LOG.md — אלגוריתמים/דגלים + מסקנות + קישור למניפסט ב־run_outputs/research_runs/.")

    if failures:
        print(f"\nFailed ({len(failures)}): {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
