# פרוטוקול נמל בית (Baseline Protocol)

כדי לא ללכת לאיבוד — תמיד יש לך עוגן לחזור אליו.

---

## 1. חוק גרסת הזהב

**אל תשנה את `stat_only` ב־`config/backtest_modes.json`.**

- הקובץ הוא "ספר החוקים"
- ניסויים חדשים מקבלים **שם חדש** (למשל `test_ml_v2`)
- אם ניסוי נכשל: `python scripts/run_backtest.py --mode stat_only`

---

## 2. יומן טיסה (Flight Log)

כל הרצה נשמרת אוטומטית ב:
```
results/YYYY-MM-DD_HHMM_symbol_mode.json
```

לדוגמה: `results/2026-03-08_0915_AAPL_stat_only.json`

---

## 3. היררכיית הבדיקות

| שלב | פקודה | זמן | מטרה |
|-----|-------|-----|------|
| Smoke | `--smoke` | ~2 דקות | האם הקוד רץ? |
| Baseline | `--mode stat_only` | ~3 דקות | האם עדיין 20%+? |
| Challenger | `--mode ml_threshold_050` | ~10 דקות | המודל החדש |

**אל תריץ Challenger לפני ש־Baseline עבר.**

---

## 4. Git Branches

לפני שינוי "מפחיד" במנוע (למשל GARCH, ARIMA):
```bash
git checkout -b feature/new-garch-logic
```

---

## 5. לוח שיאנים

עדכן `BASELINE_RECORDS.md` כשאתה שובר שיא.
