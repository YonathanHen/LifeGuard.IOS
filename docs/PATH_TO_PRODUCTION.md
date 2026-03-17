# SignalFlow — Path to Production

*צ'קליסט: מ-Backtest ל-Live Trading*

---

## סטטוס נוכחי

### ✅ הושלם

| פריט | תיאור |
|------|--------|
| Stat Core | ARIMA+GARCH+Regime+Cross-asset — יציב |
| Strategy combinations | MR x2, ATR Stop, Vol Target — best_combo אומת |
| Backtest 3y | Sharpe ~2, Return 63–77%, DD סביר |
| Backtest 5y | Return 38–143% (תלוי אסטרטגיה), תיעוד ב-Period_5Y |
| Reproducibility | git_commit, costs_included, --end-date |
| Paper Trading | paper_trading_daily.py — תמיכה ב־--no-ml (Stat Only) |
| Paper vs Backtest | paper_vs_backtest_compare.py — כלי השוואה |
| Documentation | STRATEGY_COMPARE_RESULTS, REPRODUCIBILITY, ALGORITHM_SPEC |

### ⏳ נדרש לפני Live

| # | משימה | תיאור | סטטוס |
|---|--------|-------|--------|
| 1 | **Paper Trading 6–9 חודשים** | הרצה יומית, רישום החלטות | הפעיל ותריץ |
| 2 | **השוואת Paper vs Backtest** | כל חודש: `paper_vs_backtest_compare.py` | כלי מוכן |
| 3 | **Multi-symbol validation** | הרצת best_combo על SPY, QQQ בנוסף ל-AAPL | 5y ריצה — תיעוד |
| 4 | **Circuit Breaker** | עצירה ב-DD ≥ 15% + Drawdown Throttle | ✅ מיושם (`--circuit-breaker 0.15 --drawdown-throttle`) |
| 5 | **תנאי Go/No-Go** | לפי GO_NO_GO_FRAMEWORK.md | מסמך קיים |

---

## סדר פעולות מומלץ

### שלב 1: הפעלת Paper (עכשיו)

```bash
# הרצה יומית (Task Scheduler / cron) — Stat Only כדי להתאים ל-best_combo
python scripts/paper_trading_daily.py --symbol AAPL --no-ml

# או Batch להשלמת תקופה
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --batch-start 2025-01-01 --batch-end 2026-03-17
```

### שלב 2: השוואה חודשית

```bash
python scripts/paper_vs_backtest_compare.py --symbol AAPL
```

### שלב 3: אימות 6–9 חודשים

- Paper רצה בהצלחה כל יום
- Paper vs Backtest — התאמה סבירה (diff < 15%)
- אין regressions ב-Stat Core

### שלב 4: Go/No-Go

- עיין ב-`GO_NO_GO_FRAMEWORK.md`
- החלטה: מעבר ל-Live או המשך Paper

---

## קבצים רלוונטיים

| קובץ | תפקיד |
|------|--------|
| `scripts/paper_trading_daily.py` | רישום החלטות יומי (--no-ml = Stat Only) |
| `scripts/paper_vs_backtest_compare.py` | השוואת Paper ל-Backtest |
| `storage/paper_decisions.json` | החלטות שנשמרו |
| `docs/GO_NO_GO_FRAMEWORK.md` | קריטריוני Go/No-Go |
| `docs/REPRODUCIBILITY.md` | פרוטוקול שחזור |
| `docs/PERIOD_5Y_AND_MULTI_SYMBOL_RESULTS.md` | תוצאות 5y ו-multi-symbol |
| `docs/IMPROVEMENTS_IMPLEMENTATION.md` | Circuit Breaker, DD-Throttle, Degradation, Walk-Forward, Event Filter |

---

## אזהרות

- **Hunter (ML)** ב-NO-GO — אל תשתמש ב-LSTM למסחר.
- **נתונים** — Yahoo/FRED עשויים להשתנות; הפעל עם `--end-date` לשחזור.
- **מינוף** — best_combo כולל MR x2 ב-mean_reverting; Max DD עד ~17%.

---

*נוצר: 2026-03 — חלק מתהליך Path to Production*
