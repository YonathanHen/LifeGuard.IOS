# יומן מסקנות מחקר — SignalFlow

מסמך **חי**: רושמים כאן החלטות אחרי ניסויים, כדי שאפשר יהיה לחזור אליהן בלי לזכור בעל פה.

**חובה בכל רשומה חדשה (מעכשיו והלאה):**

1. **אלגוריתמים ודגלים** — מה הופעל בפועל: סקריפט, פרופיל (`best_combo` / `production`), `BacktestEngine` (Stat / Stat+ML, `ml_negative_filter`, `ml_disaster_threshold`, `low_vol_tilt`, `dual_momentum`, `mean_rev_mult`, ATR, vol target, וכו’), תקופה, יקום / סימבול, עלויות.
2. **תוצאות** — מספרים (טבלה או בולטים): Sharpe, DD, תשואה, מספר עסקאות / ממוצעי יקום לפי הצורך.  
   **משפט קבוע לבהירות (חובה כשיש גם מניה בודדת וגם יקום באותו ניסוי):**  
   *«תשואה מצטברת על [שם המניה הבודדת]: …; ממוצע פשוט על [כמה] מניות מהיקום: …»* — שני המספרים חייבים להופיע, כדי שלא יבלבלו ביניהם.
3. **מסקנות** — מה נשמר, מה לא, מה להריץ הלאה; לא רק “הרצנו”.

**מקורות עזר לעת העתקה:** שדה `engine` ב־`config/research_run_matrix.yaml`, ומניפסט `storage/research_runs/_suite_manifest_*.json` (אחרי `run_research_suite.py`).

**איך מוסיפים רשומה:**  
העתיקו את תבנית הרשומה בתחתית, מלאו את כל השדות. **פלטי הרצות לתיעוד:** `run_outputs/` (ראו `run_outputs/README.md`) — נגישים לגיט ולסוכן; `storage/` נשאר מקומי (מראה ל־backtest_runs ודגימות).

**מסמכים קשורים:**  
`docs/SIMPLE_SYSTEM_EXPLANATION_HE.md` (הסבר פשוט: רכיבים, שם באנגלית + תיאור בעברית, למה מניה בודדת מול ממוצע יקום), `docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md` (דירוג יקום + תיק — שלבים, דגלים, `rank_universe.py`), `docs/RECOMMENDED_ENHANCEMENTS_AB.md` (פרוטוקול A/B), `docs/WORKING_MULTI_UNIVERSE_PROFILES.md` (multi-symbol: ברירת מחדל vs production + דגלים), `docs/RESEARCH_RUN_SUITE.md` (מטריצת ריצות מבודדות + `run_research_suite.py`), `RESULTS_SUMMARY.md`, `ALGORITHM_SPEC.md`.

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

**בקטסט הראשי (מומלץ לשגרה):**

```powershell
python scripts/run_backtest_with_ml.py --period 3y --low-vol-tilt --label stat_ml_lowvol_3y
```

קוד: `BacktestEngine(..., low_vol_tilt=True)` — ראו `backtesting/engine.py`.

---

## רשומה #2 — יקום 10 סימבולים: `best_combo` מול `production` מול `production` + `low_vol` (3y)

| שדה | ערך |
|-----|-----|
| **תאריך** | 2026-04-22 (הרצה מקומית) |
| **ניסוי** | `python scripts/run_research_suite.py --only m01_multi_best_combo,m03_multi_production,m04_multi_production_lowvol` |
| **אלגוריתמים ודגלים** | ראו שדות `engine` למזהים m01/m03/m04 ב־`config/research_run_matrix.yaml` ובמניפסט `_suite_manifest_20260422_204756.json` (שדה `runs[].engine`). |
| **תצורה** | אותם 10 סימבולים ראשונים מהיקום (`config/symbols.yaml`, `--limit 10`), תקופה **3y**, עלויות ברירת מחדל בסקריפט |
| **מטרה** | לבדוק אם פרופיל **production** (Stat+ML) משפר ממוצעים על יקום מול **best_combo**, ומה תרומת **`low_vol_tilt`** על production |

### תוצאות — ממוצעים (10 סימבולים)

| ריצה | פרופיל | Avg Return | Avg Sharpe | Avg DD |
|------|--------|------------|------------|--------|
| **m01** | `best_combo` | **19.7%** | **0.584** | -16.3% |
| **m03** | `production` | 6.5% | 0.334 | -16.1% |
| **m04** | `production` + `low_vol_tilt` | 7.1% | 0.373 | **-13.9%** |

**משפט בהירות:** תשואה מצטברת על אפל ב־m01 (בדיקת עבר, אותה תצורה): בערך **+37%** על כמעט שלוש שנים; ממוצע פשוט על **עשר** מניות ראשונות מהיקום באותה ריצה: **+19.7%** — שני מספרים שונים, שניהם נכונים.

### תצפיות לפי סימבול (מהדפסות טרמינל; פירוט מלא ב־JSON)

- חזקות ב־**m01**: AAPL, GOOGL; חלשות: MSFT, PG, AMZN, NVDA (Sharpe שלילי / הפסדים חמורים בחלקן).
- **m04** לעומת **m01** על אותן מניות: דפוס עקבי של **הקטנת נזק** ב־AMZN/NVDA (פחות הפסד ו־DD), שיפור קל ב־MSFT; GOOGL כמעט ללא שינוי; AAPL במסלול מוכר של low_vol (פחות DD, פחות תשואה גולמית).

### מסקנות מאושרות (נכון לרשומה זו)

1. **על היקום והחלון שנבדק:** **`best_combo` מנצח בממוצע** בתשואה וב־Sharpe לעומת **production** (m03). כלומר Stat+ML בסגנון `run_backtest_with_ml` **לא הוכח כמעלה ממוצעת** מול legacy על רשימת העשר בלי כוונון נוסף.
2. **`low_vol_tilt` על production (m04 מול m03):** **שיפור** בממוצע — תשואה קלה יותר, Sharpe גבוה יותר, **DD ממוצע רדוד יותר** (−13.9% לעומת −16.1%). עקבי עם רשומה #1 (ריסק־מתוקן), הפעם על יקום.
3. **m04 מול m01:** עדיין **פיגור בתשואה וב־Sharpe**; **יתרון** ב־**DD ממוצע** (−13.9% לעומת −16.3%). בחירה בין legacy לבין production+low_vol היא **trade-off** תשואה/Sharpe מול עומק DD ממוצע.
4. **אסטרטגיה:** המנוע **לונג או מזומן בלבד** — אין שורט; ירידות “נתפסות” רק עד כדי **יציאה/הקטנת חשיפה**, לא כרווח מכיוון שלילי.

### שחזור וקבצים

```powershell
python scripts/run_research_suite.py --only m01_multi_best_combo,m03_multi_production,m04_multi_production_lowvol
```

**גולם:**  
מעודכן לנתיב **`run_outputs/research_runs/`** (ראו `run_outputs/README.md`): `suite_m01_best_combo_3y.json` · `suite_m03_production_3y.json` · `suite_m04_production_lowvol_3y.json` · מניפסט `_suite_manifest_*.json`. ריצות ישנות עשויות עדיין להופיע תחת `storage/` מקומי.

---

## תבנית לרשומה הבאה

```
## רשומה #N — [כותרת קצרה]

| שדה | ערך |
|-----|-----|
| **תאריך** | YYYY-MM-DD |
| **פקודה / סקריפט** | הפקודה המלאה (או run id מהסוויטה) |
| **אלגוריתמים ודגלים** | Stat / ML, פרופיל, thresholds, low_vol, dual, מגבלות יקום, bps — או הפניה לשדה engine במניפסט |
| **מטרה** | מה בודקים |
| **משפט בהירות** | תשואה מצטברת על …: …; ממוצע פשוט על … מניות: … (אם רלוונטי) |
| **תוצאות** | טבלה / נקודות עיקריות |
| **מסקנות** | החלטה מפורשת; המשך מוצע |
| **קבצים** | JSON / manifest / backtest_runs label |
```

---

*נוצר כדי שלא “נשכח” בדיקות — עדכנו את המסמך בכל החלטה משמעותית.*
