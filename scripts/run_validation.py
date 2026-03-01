#!/usr/bin/env python
"""
SignalFlow — הרצת אימות Point-in-Time
בודק 15 מדגמים לכל horizon על תאריכים רנדומליים מההיסטוריה.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from validation.point_in_time import run_validation


def main():
    print("=" * 60)
    print("SignalFlow — Point-in-Time Validation")
    print("15 samples per horizon, random past dates, no future info")
    print("=" * 60)

    try:
        results = run_validation(
            symbol="AAPL",
            samples_per_horizon=15,
            seed=42,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    for horizon, vr in results.items():
        print(f"\n--- {horizon.upper()} ---")
        print(f"  Total (with direction): {vr.total}")
        print(f"  Correct: {vr.correct}")
        print(f"  Incorrect: {vr.incorrect}")
        print(f"  Skipped (flat): {vr.skipped_flat}")
        if vr.total > 0:
            acc = vr.correct / vr.total * 100
            print(f"  Accuracy: {acc:.1f}%")
        print("\n  Samples:")
        for s in vr.samples:
            res = s.get("result", s.get("error", "?"))
            print(f"    {s.get('date', '?')}: pred={s.get('direction', '?')}, "
                  f"actual={s.get('actual_ret', '?')}% -> {res}")

    print("\n" + "=" * 60)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
