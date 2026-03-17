# SignalFlow — פרוטוקול שחזור תוצאות

*כיצד לשחזר תוצאות backtest בדיוק — גם אחרי שינויים בקוד*

---

## 1. מה נשמר בכל הרצה

| שדה | מיקום | תיאור |
|-----|-------|--------|
| `params` | results/*.json, strategy_compare | כל הפרמטרים (commission_bps, slippage_bps, mode, flags) |
| `git_commit` | results/*.json, strategy_compare | Hash של ה-commit הנוכחי |
| `end_date` | כשמועבר | תאריך סיום קבוע — חלון הזמן לא "זז" |
| `costs_included` | true | העמלות (5+3 bps) תמיד כלולות |

---

## 2. שחזור תוצאה ספציפית

### שלב 1: חזרה ל-commit

```bash
git checkout <git_commit>
# או: git checkout e255321  # מתוך ה-JSON שנשמר
```

### שלב 2: הרצה עם אותם פרמטרים

```bash
python scripts/run_backtest.py \
  --mode stat_only \
  --period 3y \
  --end-date 2026-03-02 \
  --mean-rev-mult 2.0
```

הפרמטרים המלאים נמצאים ב-`params` בקובץ ה-JSON.

### שלב 3: השוואה

התוצאות (Sharpe, Return, DD, Trades) אמורות להיות זהות. אם לא — ייתכן שינוי בנתונים (Yahoo/FRED מעדכנים היסטוריה).

---

## 3. מגבלות שחזור

| גורם | ניתן לשליטה? | הערה |
|------|---------------|------|
| קוד | כן | `git checkout <commit>` |
| פרמטרים | כן | נשמרים ב-JSON |
| תאריך סיום | כן | `--end-date` |
| נתוני Yahoo/FRED | לא | Yahoo עשוי לעדכן מחירים היסטוריים |
| גרסאות חבילות | חלקי | `requirements.txt` — לא נשמר per-run |

---

## 4. קבצי תוצאות

| קובץ | תוכן |
|------|------|
| `results/YYYY-MM-DD_HHMM_{symbol}_{mode}.json` | הרצה בודדת (run_backtest) |
| `storage/strategy_compare_results.json` | השוואת אסטרטגיות |
| `storage/backtest_runs.json` | run_backtest_with_ml |

---

## 5. טיפ: שמירת snapshot לפני שינוי גדול

```bash
# שמור את המצב הנוכחי
git rev-parse HEAD > storage/last_baseline_commit.txt
python scripts/run_backtest.py --mode stat_only --period 3y --end-date 2026-03-02
# התוצאות יישמרו עם git_commit ב-results/
```

---

*נוצר: 2026-03 — חלק מתהליך Reproducibility*
