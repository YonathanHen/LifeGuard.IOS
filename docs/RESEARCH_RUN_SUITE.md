# סוויטת ריצות מחקר (מבודדות, עם דגלים)

מטרה: להריץ **את כל ההצעות שדיברנו עליהן** בנפרד — כל ריצה עם **פלט משלה**, בלי לשנות ברירות מחדל בקוד ובלי לערבב תרחישים באותו קובץ (חוץ מ־`run_enhancement_ab` שמיועד בכוונה לטבלה אחת **פנימית**).

---

## איך זה משתלב במה שכבר יש

| רכיב קיים | תפקיד |
|-----------|--------|
| **`run_backtest_with_ml.py`** | מסלול יומיומי; הסוויטה רק מוסיפה `--label` ייחודי לכל ריצה כדי שיופיעו נפרדים ב־`storage/backtest_runs.json` |
| **`run_multi_universe.py`** | אותו קוד; הסוויטה קוראת עם `--profile` / דגלים ו־`--out` ל־`storage/research_runs/*.json` |
| **`run_enhancement_ab.py`** | סוללת A/B; הסוויטה שומרת JSON תחת `storage/research_runs/suite_ab_*.json` (לא דורס את `storage/enhancement_ab_*.json` הישנים אלא אם תשנה YAML) |
| **`docs/WORKING_MULTI_UNIVERSE_PROFILES.md`** | מפרט **מה** כל פרופיל עושה; הסוויטה רק **מריצה** את השילובים המומלצים לניתוח |
| **`docs/NEXT_EXECUTION_PLAN.md`** | שלבים 1–2; הריצות `s*` ו־`m*` תואמים לשם |

---

## פקודות

```powershell
cd C:\Users\Yonat\PycharmProjects\SignalFlow

# רשימת כל הריצות (אחרי סינון)
python scripts/run_research_suite.py --list

# סימולציה בלי להריץ
python scripts/run_research_suite.py --dry-run

# רק סימבול בודד / רק יקום / רק A/B
python scripts/run_research_suite.py --group single
python scripts/run_research_suite.py --group multi
python scripts/run_research_suite.py --group ab

# הכל, עם חלון קצר יותר ויקום קטן (עשירייה → שלושה סימבולים, תקופה מקוצרת)
python scripts/run_research_suite.py --quick

# ריצות ספציפיות (מזהים מ-config/research_run_matrix.yaml)
python scripts/run_research_suite.py --only s01_bwml_baseline,s02_bwml_lowvol
```

אחרי הרצה אמיתית נוצר **`storage/research_runs/_suite_manifest_*.json`** עם הפקודות, **קודי יציאה**, ושדה **`engine`** לכל ריצה (סיכום אלגוריתמים/דגלים מ־`config/research_run_matrix.yaml`).

### תיעוד חובה אחרי כל סוויטה / ניסוי

1. פתח את המניפסט האחרון והעתק ל־**`docs/RESEARCH_DECISIONS_LOG.md`** רשומה חדשה לפי התבנית שבתחתית אותו מסמך.  
2. חובה: **אלגוריתמים ודגלים**, **תוצאות עיקריות**, **מסקנות**, **נתיבי קבצי גולם**.  
3. הרצות **מחוץ** לסוויטה (למשל `run_backtest_with_ml` ידנית) — אותו עיקרון: רשומה מלאה ביומן.

---

## איפה הפלטים

| סוג | מיקום |
|-----|--------|
| בקטסט עם ML (סימבול בודד) | `storage/backtest_runs.json` — לפי שדה `label` (`suite_s01_...`) |
| יקום / A/B מהסוויטה | `storage/research_runs/suite_*.json` |
| מניפסט | `storage/research_runs/_suite_manifest_*.json` |

---

## התאמה אישית

ערוך **`config/research_run_matrix.yaml`**: הוסף ריצה עם `id` חדש, `group`, שדה **`engine`** (שורה אחת שמסכמת אלגוריתמים + דגלים), ו־`args` (רק דגלים שקיימים בסקריפט המטרה). אין צורך לגעת במנוע.

---

*הסוויטה לא מפעילה Paper Trading — זה נשאר ידני לפי `NEXT_EXECUTION_PLAN`.*
