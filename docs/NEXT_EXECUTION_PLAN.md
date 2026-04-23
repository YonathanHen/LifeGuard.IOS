# תוכנית ביצוע — SignalFlow (המשך מסודר)

*איך מתקדמים מהמצב הנוכחי — בלי לפרק את מה שעובד.*

**מסמכי עוגן:** `GO_NO_GO_FRAMEWORK.md` · `RESEARCH_DECISIONS_LOG.md` · `RECOMMENDED_ENHANCEMENTS_AB.md`

---

## שלב 0 — כבר יש (לא לשבור)

- Stat Core + Regime + Rules + ML (Negative Filter).
- יומן מחקר + A/B “helpful” + JSON לשחזור.
- **`low_vol_tilt`** כאופציה מאושרת (Sharpe↑, DD↓, תשואה גולמית קצת↓) — ראו רשומה #1 ביומן.

---

## שלב 1 — הרצה יומיומית על אותה תוכנית (שבוע–חודש)

| # | משימה | פעולה |
|---|--------|--------|
| 1.1 | בקטסט ראשי עם שיפור מאושר | `python scripts/run_backtest_with_ml.py --period 3y --low-vol-tilt` (+ `--label stat_ml_lowvol_3y`) |
| 1.2 | השוואה ל-baseline | אותה פקודה **בלי** `--low-vol-tilt` — לוודא שהפער עדיין כמו ביומן |
| 1.3 | Paper Trading | `paper_trading_daily.py` לפי `PAPER_TRADING_IMPLEMENTATION_PLAN.md` |

**אופציונלי:** `--dual-momentum` — בהרצה שלכם לא נתן תוספת מול baseline; אפשר להשאיר כבוי או לבדוק שוב אחרי שנה.

---

## שלב 2 — Multi-symbol (אותו קוד, בלי tuning)

| # | משימה | פעולה |
|---|--------|--------|
| 2.1 | Universe עם פרופיל ייצור | `python scripts/run_multi_universe.py --profile production --period 3y --limit 10 --low-vol-tilt --out storage/multi_....json` — ראו [`WORKING_MULTI_UNIVERSE_PROFILES.md`](WORKING_MULTI_UNIVERSE_PROFILES.md) |
| 2.2 | או סימבול-סימבול | `run_backtest_with_ml.py --symbol SPY` וכו' |
| 2.3 | רישום תוצאות | רשומה ב־`RESEARCH_DECISIONS_LOG.md` + JSON מ־`--out` |

---

## שלב 3 — Gate 2 (אחרי 3+ חודשי Paper)

| # | משימה | פעולה |
|---|--------|--------|
| 3.1 | דוח | `paper_trading_report.py` |
| 3.2 | החלטה | `GO_NO_GO_FRAMEWORK.md` — Net EV, Blocked Loss Rate, וכו' |

---

## שלב 4 — רק אחרי Gate 2 ירוק

- **איך לבדוק כיוונים מוסדיים (פקטורים, חתך, LTR):**  
  [`INSTITUTIONAL_DIRECTIONS_FEASIBILITY.md`](INSTITUTIONAL_DIRECTIONS_FEASIBILITY.md)
- Factor נוסף (מומנטום 12-1 כפילטר נפרד — כבר בקוד; **לא** לאמץ בלי A/B חוזר).
- הרחבות מ־`ALGORITHMIC_STRATEGIES_CATALOG_RESEARCH.md`.

---

## פקודות שורה אחת (לעת עתה)

**או:** סוויטה מסודרת (ריצות מבודדות, דגלים בלבד) — `docs/RESEARCH_RUN_SUITE.md` · `python scripts/run_research_suite.py --list`

```powershell
# Baseline (להשוואה)
python scripts/run_backtest_with_ml.py --period 3y --label baseline_3y

# פרופיל “יותר Sharpe / פחות DD” (מאושר ביומן)
python scripts/run_backtest_with_ml.py --period 3y --low-vol-tilt --label stat_ml_lowvol_3y

# סוללת A/B (כמו קודם)
python scripts/run_enhancement_ab.py --battery helpful --period 3y --symbol AAPL --with-ml --json-out storage/enhancement_ab_helpful_3y_ml.json
```

---

*עדכנו את המסמך כששלב נסגר או משתנה עדיפות.*
