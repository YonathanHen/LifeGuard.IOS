# SignalFlow — תוכנית מוכנות למסחר

*מסמך מסודר: מצב נוכחי • מה נעשה • סדר ביצוע • הערכה לאחר השלמה*

---

## חלק א׳ — מצב נוכחי (לפני השלמת התוכנית)

### 1.1 מה יש ומה עובד

| רכיב | סטטוס | הערות |
|------|--------|-------|
| **Stat Core** | ✔ מלא | ARIMA, GARCH, HMM, Rule Engine |
| **External Features** | ✔ מלא | VIX, FRED (credit_spread, yield_curve), shift(1) |
| **LSTM** | ✔ מלא | returns + VIX + credit_spread + yield_curve |
| **ML רק ב־Daily** | ✔ מלא | API + Validation |
| **Point-in-Time Validation** | ✔ מלא | 40 תאריכים, אין look-ahead ב־inputs |
| **API** | ✔ מלא | GET /predict מחזיר P_up, P_down |

### 1.2 מה חסר למסחר

| רכיב | סטטוס | השפעה |
|------|--------|-------|
| **Calibration** | סקריפט קיים, חסרונות | סף 0.6 שרירותי — לא מותאם לנתונים |
| **Backtest עם ML** | חסר | ה-BacktestEngine משתמש רק ב-Stat Core, לא ב-LSTM |
| **עלויות במסחר** | חסר | אין commission/slippage — תוצאות אופטימיות מדי |
| **מדדי אסטרטגיה** | חלקי | Validation מודד דיוק, לא Sharpe/Drawdown בפועל |

### 1.3 סיכום מצב

- **חיזוי:** תקין — inputs נקודתיים בזמן, מודל מאומן על היסטוריה.
- **Validation:** 83% דיוק על 6 החלטות משמעותיות (daily, Stat+ML).
- **מסחר אמיתי:** חסרים backtest עם ML, calibration, ועלויות — אין הערכה מלאה של תוחלת.

---

## חלק ב׳ — מה נעשה (מפורט)

### שלב 1: תיקון והרצת Calibration

**מה:** עדכון `scripts/calibrate_ml_threshold.py` כך שיעבוד נקודתית בזמן ויבחר סף מיטבי.

**איך:**
1. להחליף `returns.shift(-1)` ב־`_get_actual_next_return` (כמו ב-validation) — תשואה אמיתית של היום הבא.
2. להשתמש ב־`check_cross_asset_alignment_from_series` עם נתונים point-in-time (SP, VIX עד התאריך) — כמו ב-validation.
3. Grid search על ספים 0.52–0.70.
4. קריטריון: maximize Precision @ decisions — **בתנאי מינימום טריידים** (למשל 20). מונע overfitting: סף שנותן 100% על 5 טריידים ייראה מושלם ב-backtest אבל יקפא בזמן אמת.
5. לעדכן את הסף ב־API (ברירת מחדל) ובסקריפטי validation.

**פלט:** סף מומלץ (למשל 0.58 או 0.65), עדכון `api/routes/predictions.py`.

---

### שלב 2: הרחבת BacktestEngine עם שכבת ML

**מה:** הוספת LSTM ל-backtest — ביום i: אם Stat Edge + ML מסכים (P > threshold) → Long, אחרת Flat.

**איך:**
1. ב־`backtesting/engine.py`:
   - טעינת LSTM מ־storage.
   - ב־horizon=daily: לכל יום — pipeline עם end_date=יום הנוכחי, predict_proba, ensemble_decision.
   - pos = 1 רק אם has_edge_stat **וגם** has_edge_ensemble (ML אישר).
   - כרגע: רק Long — Short לא מיושם (עקבי עם המצב הנוכחי).
2. פרמטר `use_ml: bool = True` — לאפשר השוואה Stat vs Stat+ML.

**ביצועים:** הרצת predict_proba בתוך לולאה על שנים עלולה להיות איטית. **Pre-compute:** להכין מראש וקטור תחזיות לכל תאריכי ה-backtest, וה-Engine ימשוך ממנו — חוסך זמן משמעותי.

---

### שלב 3: הוספת עלויות למסחר

**מה:** Commission + Slippage — לשקף מציאות.

**איך:**
1. פרמטרים: `commission_bps` (למשל 5 = 0.05%), `slippage_bps` (למשל 3). סה״כ 0.08% לכל צד, 0.16% לסיבוב מלא — הוגן ושמרני ל-AAPL (נזילות גבוהה).
2. בכל מעבר מ-Flat→Long: חיסור `(commission + slippage) * 2` (כניסה ויציאה) מהתשואה של אותו יום.
3. ברירת מחדל: 5 bps commission, 3 bps slippage — ניתן לכבות (0) לבדיקה.

**דגש:** אם ה-ML גורם ל־Churning (כניסה/יציאה כל יום), העמלות "יחוררו" את התיק. ה-Backtest יראה מיד אם ML משפר **איכות** או רק מעלה **כמות** עסקאות לחינם.

---

### שלב 4: סקריפט הרצה ודוח

**מה:** `scripts/run_backtest_with_ml.py` — מריץ backtest Stat בלבד vs Stat+ML, מדפיס דוח.

**איך:**
1. הרצת BacktestEngine עם use_ml=False, use_ml=True.
2. הדפסת:
   - Sharpe, Max Drawdown, Total Return, N Trades, Hit Rate
   - **Exposure (Time in Market)** — כמה זמן בתוך השוק. אם ML מסנן מדי, 90% מחוץ לשוק — האם התשואה העודפת שווה את ההזדמנויות שהפסדת?
   - השוואה בין Stat בלבד ל־Stat+ML
3. **Equity Curve Visualization** — גרף שמשווה Stat vs Stat+ML. לפעמים רואים בעין שה-ML מונע Drawdown ספציפי גדול — שווה יותר מכל מספר יבש.
4. אופציונלי: שמירת equity_curve לקובץ.

**פלט:** דוח ברור — האם ה-ML משפר את הביצועים בפועל.

---

## חלק ג׳ — סדר ביצוע

```
1. Calibration (תיקון + הרצה + עדכון סף)
       ↓
2. BacktestEngine + ML
       ↓
3. עלויות (commission, slippage)
       ↓
4. run_backtest_with_ml.py + דוח
       ↓
5. בדיקות סיכון: Threshold Stability (±0.02), Regime Sensitivity
       ↓
6. בדיקות איכות: Decision Density, Error Type Analysis
       ↓
7. קו אדום → החלטה: Paper Trading / לא
       ↓
8. עדכון מסמכים (STATUS, IMPROVEMENTS)
```

**לוגיקה:** קודם סף (1), backtest (2–4), בדיקות יציבות (5–6), החלטה (7).

---

## חלק ד׳ — הערכה לאחר השלמה

### מה נדע

| שאלה | תשובה |
|------|--------|
| איזה סף ML אופטימלי? | מהרצת Calibration |
| האם ML משפר Sharpe/Drawdown? | מהשוואת Backtest Stat vs Stat+ML |
| מה התוחלת אחרי עלויות? | מתוצאות עם commission+slippage |
| האם כדאי לסחור? | החלטה מבוססת נתונים |

### תרחישים אפשריים

| תוצאה | משמעות |
|-------|--------|
| **Stat+ML > Stat** (Sharpe גבוה יותר, Drawdown נמוך) | ML מוסיף ערך — מומלץ לשימוש |
| **Stat+ML ≈ Stat** | **סימן טוב.** ML משמש כ־*Safety Filter* — לא הרס את ה-Edge אלא אישר. שווה המון במסחר אמיתי. |
| **Stat+ML < Stat** | ML מזיק — להשתמש ב-Stat בלבד |
| **Sharpe שלילי / Drawdown גבוה** | האסטרטגיה לא רווחית — paper trading או הימנעות |

### גבולות

- **אין Short** — כרגע רק Long. אם הכיוון down — Flat.
- **אין Position Sizing** — כל פוזיציה 100%.
- **Walk-forward training** — לא מיושם (המודל אומן פעם על 5y).
- **נכס בודד** — AAPL. הרחבה ל־נכסים נוספים — שלב מאוחר.

---

## חלק ה׳ — דגשים מהנדסיים

| עיקרון | יישום |
|--------|--------|
| **הפרדה: חיזוי vs מסחר** | חיזוי (LSTM) = כבר קיים. מסחר = אופטימיזציה של אסטרטגיה + עלויות. |
| **מדדים: ML vs כסף** | המעבר מ־Accuracy (מדד ML) ל־Sharpe/Drawdown (מדדי כסף) הוא לב התוכנית. |
| **Overfitting ב-Calibration** | מינימום טריידים (20) — מונע סף "מושלם" על 5 דגימות. |
| **Stat+ML ≈ Stat** | לא כישלון — ML כ־Safety Filter שווה במסחר אמיתי. |
| **Exposure** | Time in Market — אם ML מסנן מדי, בודקים האם שווה. |
| **ויזואליזציה** | Equity Curve על הגרף — לפעמים Drawdown שנחסך רואים בעין. |

---

## חלק ז׳ — בדיקות סיכון (חובה)

### 7.1 יציבות הסף (Threshold Stability)

אחרי Calibration — **לא להסתפק במספר אחד.**

**בדיקה נדרשת:** להריץ backtest עם הסף שנבחר **±0.02** (למשל 0.58 / 0.60 / 0.62).

| מה מחפשים | משמעות |
|------------|--------|
| ביצועים מתרסקים בשינוי קטן | הסף לא יציב → overfitting סמוי |
| ביצועים דומים | הסף בר־הגנה |

**כלל זהב:** סף מעט פחות אופטימלי אך יציב > סף מושלם אך שביר.

### 7.2 רגישות ל-Regime (שקט / תנודתיות)

כבר יש HMM — יתרון. צריך לבדוק: האם ML עובד טוב יותר ב־Low Vol או ב־High Vol?

**איך:**
1. לפצל את ה-backtest לפי regime (state=0 / state=1).
2. לחשב Sharpe ו-Drawdown לכל regime בנפרד.

**תוצאה רצויה:** ML לא חייב לנצח בכל regime — אבל **אסור** שיהיה קטסטרופלי באחד מהם.

אם ML נכשל קשות ב־High Vol → לשקול:
```python
if regime == HIGH_VOL:
    ignore ML
```
זה לא כישלון — זו בגרות הנדסית.

---

## חלק ח׳ — בדיקות איכות החלטות (לא רק כסף)

### 8.1 Decision Density Analysis

| מדד | משמעות |
|-----|--------|
| **N Trades / Year** | האם המערכת חיה או רדומה |
| **Avg Days in Trade** | האם ML חותך מהר מדי |
| **Avg Return per Trade** | איכות ההחלטה, לא הכמות |

**דגלים אדומים:**
- הרבה טריידים קטנים + תשואה כוללת שטוחה → ML מייצר רעש
- מעט טריידים עם תשואה גבוהה → ML מסנן טוב

### 8.2 ניתוח סוגי טעויות (Error Type Analysis)

לא כל טעות שווה. לכל יום שבו ML חסם טרייד — האם זה **מנע Drawdown** או **פספס Trend גדול**?

| סוג | משמעות |
|-----|--------|
| **False Negative** | פספוס רווח — חסם טרייד שכנראה היה רווחי |
| **False Positive** | כניסה לפני הפסד — נכנס, הפסנו |

**במסחר:** False Positive מסוכן יותר מ-False Negative. אם ה-ML מוריד False Positive — הוא שווה גם אם Accuracy יורד.

---

## חלק ט׳ — קו אדום לקבלת החלטה

אחרי כל השלבים — כללי החלטה חדים:

### מותר לעבור ל-Paper Trading אם

- Sharpe ≥ Stat בלבד **או**
- Max Drawdown נמוך יותר ב־≥15%
- **וה־Exposure ≥ 20%** (לא מערכת רדומה)

### אסור לעבור ל-Paper Trading אם

- התוצאה החיובית נובעת מ־5–10 טריידים בלבד
- שינוי סף קטן (±0.02) שובר את הביצועים
- הרווח נעלם אחרי עמלות

---

## חלק י׳ — מה לא לעשות עכשיו

| ❌ | סיבה |
|----|------|
| לא להוסיף עוד Features | פתיחת דלת ל-overfitting חדש |
| לא להוסיף Short | מורכבות, אין עדיין לוגיקה |
| לא לשנות Architecture | שלב הוכחה, לא פיתוח |
| לא לאמן מחדש LSTM | מודל קבוע — מוכיחים את הקיים |

**עכשיו זה שלב הוכחה, לא שלב פיתוח.**

---

## חלק יא׳ — תמונת מצב אמיתית

מה שיש עכשיו:

- מערכת חיזוי נקייה מ-lookahead
- הפרדה נכונה בין ML → Decision → Money
- הבנה שה-ML הוא **Filter**, לא Oracle

**זה המקום שבו 90% מהפרויקטים נופלים — ואתה לא שם.**

מטרה: להפוך את ה־83% דיוק ליתרון כספי **אמיתי, יציב ובר־הגנה**.

---

## חלק יב׳ — מסמכי ייחוס

| מסמך | תפקיד |
|------|--------|
| **ROADMAP_V2.md** | תכנון כללי |
| **IMPROVEMENTS_PROPOSAL.md** | שיפורים מפורטים |
| **STATUS_AND_RECOMMENDATIONS.md** | ניתוח בעיה והמלצות |
| **TRADING_READINESS_PLAN.md** (זה) | תוכנית מוכנות למסחר |

---

---

## נספח — מה יושם (2026-03)

| שלב | יישום |
|-----|--------|
| 1. Calibration | `scripts/calibrate_ml_threshold.py` — point-in-time, min 20 trades, cross-asset |
| 2. BacktestEngine + ML | `backtesting/engine.py` — use_ml, ml_threshold, pre-compute, regime breakdown |
| 3. עלויות | commission_bps, slippage_bps (5+3 default), round-trip on entry |
| 4. run_backtest_with_ml | `scripts/run_backtest_with_ml.py` — Stat vs Stat+ML, Decision Density, Threshold Stability |
| API | ML_THRESHOLD env — עדכון ברירת מחדל אחרי calibration |

**הרצה:** `python scripts/run_backtest_with_ml.py --period 3y --stability`

---

*מסמך תוכנית — גרסה 1.2 — SignalFlow*
