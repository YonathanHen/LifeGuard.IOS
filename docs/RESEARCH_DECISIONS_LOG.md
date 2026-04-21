# יומן מסקנות מחקר — SignalFlow

מסמך **חי**: רושמים כאן החלטות אחרי ניסויים, כדי שאפשר יהיה לחזור אליהן בלי לזכור בעל פה.

**איך מוסיפים רשומה חדשה:**  
העתיקו את תבנית הרשומה בתחתית, מלאו תאריך, ניסוי, מסקנה, קבצים. שמרו את תוצאות הגולם ב־`storage/*.json`.

**מסמכים קשורים:**  
`docs/RECOMMENDED_ENHANCEMENTS_AB.md` (פרוטוקול A/B), `RESULTS_SUMMARY.md`, `ALGORITHM_SPEC.md`.

---

## רשומה #1 — סוללת “helpful” (שיפורי roadmap) — Stat+ML, 3y

| שדה | ערך |
|-----|-----|
| **תאריך** | 2026-02 (הרצה מקומית) |
| **ניסוי** | `python scripts/run_enhancement_ab.py --battery helpful --period 3y --symbol AAPL --with-ml --json-out storage/enhancement_ab_helpful_3y_ml.json` |
| **תצורה** | Stat+ML, Negative Filter (ברירת מחדל ~0.80), `refit_every=5`, עלויות 5+3 bps |
| **מטרה** | לבדוק אם `low_vol_tilt` / `dual_momentum` משפרים על baseline |

### תוצאות (מקור: `storage/enhancement_ab_helpful_3y_ml.json`)

| תרחיש | Sharpe | Max DD | TotRet | Trades | Exp% |
|--------|--------|--------|--------|--------|------|
| baseline | 1.42 | -11.9% | **32.8%** | 150 | 31.7% |
| dual_momentum_spy | 1.42 | -11.9% | 32.8% | 150 | 31.7% |
| **low_vol_tilt** | **1.54** | **-10.3%** | 30.9% | 145 | 30.7% |
| low_vol + dual | 1.44 | -10.3% | 28.6% | 150 | 31.7% |

### מסקנה מאושרת

- **נשמרת כאופציה:** **`low_vol_tilt=True`** ב־`BacktestEngine` — פרופיל **יותר Sharpe / פחות DD**, במחיר **תשואה גולמית נמוכה יותר** מ־baseline באותו חלון.
- **לא מעדיפים כרגע:** שילוב `low_vol + dual` על פני `low_vol` לבד (Sharpe ותשואה גרועים יותר מ־low_vol לבד).
- **`dual_momentum_spy`** בהרצה זו זהה ל-baseline — להמשיך לנטר בעתיד; לא סיבה לכבות, אבל אין כאן תוספת מדידה ב-3y הזה.

### שחזור בעתיד

```powershell
python scripts/run_enhancement_ab.py --battery helpful --period 3y --symbol AAPL --with-ml --json-out storage/enhancement_ab_helpful_3y_ml.json
```

קוד: `BacktestEngine(..., low_vol_tilt=True)` — ראו `backtesting/engine.py`.

---

## תבנית לרשומה הבאה

```
## רשומה #N — [כותרת קצרה]

| שדה | ערך |
| **תאריך** | YYYY-MM-DD |
| **ניסוי** | פקודה / סקריפט |
| **מסקנה** | מה נשמר / מה לא |
| **קבצים** | storage/....json |
```

---

*נוצר כדי שלא “נשכח” בדיקות — עדכנו את המסמך בכל החלטה משמעותית.*
