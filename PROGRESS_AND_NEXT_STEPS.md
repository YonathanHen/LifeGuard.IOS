# SignalFlow — התקדמות, תוצאות ותוכנית המשך

*מסמך סיכום: מה בוצע • תוצאות הבדיקות • כיוון ההמשך*

---

## סיכום מצב נוכחי והחסם

### איפה אנחנו עכשיו

| רכיב | מצב |
|------|-----|
| **ארכיטקטורה** | Stat-Led + ML Safeguard (Negative Filter @ 0.80) — מוכנה לייצור |
| **מודל LSTM** | lookback 40, אומן על 5y — גיבוי ב־`lstm_model_backup.pt` |
| **Backtest** | Stat Core: Sharpe ~1.73, Max DD -11.3%, Hit 58%. Stat+ML דומה (ML כמעט לא מסנן בתנאים האחרונים) |
| **תצורת Success** | Legacy AND: Hit 61.4%, Sharpe 2.12, DD -3.6% — מושגת רק ב־`--no-negative-filter` |
| **Run Registry** | `storage/backtest_runs.json` — שמירה אוטומטית בכל הרצה |

### החסם העיקרי — למה מסחר טוב שעובד עדיין לא בידינו

| חסם | הסבר | סטטוס |
|-----|------|--------|
| **1. חוסר הוכחה בזמן אמת** | כל התוצאות הן backtest היסטורי. אין Paper Trading רציף, אין אימות שזה עובד ב־2025–2026. | **חסימה מבצעית** |
| **2. Alpha Decay** | המודל אומן על היסטוריה. תנאי השוק משתנים — בלי retrain תקופתי ה-ML מאבד ערך. Retrain קודם החמיר (DD 18% במקום 12%). | **חסימה אסטרטגית** |
| **3. אי-עקביות בתוצאות** | Success Config (Sharpe 0.49, Exposure 45%) מול backtest אחרון (Sharpe 1.7, Exposure 32%) — ייתכן הבדלי תקופה/נתונים. | **חוסר וודאות** |

### מה נדרש כדי להגיע למסחר טוב שעובד

1. **מבצעי:** הרצת Paper Trading 3–6 חודשים — אימות שהמערכת מחזירה החלטות סבירות בלי כסף אמיתי. עם מדדי אמון (Decision Consistency, Blocked Loss Rate, Regret) — לא רק PnL.
2. **אסטרטגי:** Walk-Forward Retrain מתוזמן (רבעוני), עם Model Promotion קפדני (Sharpe ≥ 0.49, DD ≤ 12%).
3. **תיעוד:** שמירה אוטומטית בכל הרצה ל־`storage/backtest_runs.json`.

### Error Type Analysis + Expected Value (הושלם)

ב־`--stability` המערכת מציגה כעת:

| מדד | משמעות |
|-----|--------|
| **Sum Saved** | סכום ההפסדים שנמנעו (ML חסם, מחיר ירד) |
| **Sum Missed** | סכום הרווחים שפוספסו |
| **Net EV** | Sum Saved − Sum Missed — אם חיובי, ה-ML מוכיח את עצמו כסוכן סיכון |
| **Mean blocked loss** | ממוצע הפסד שנחסם (האם ML חוסם הרבה קטנים או מעט עם זנב שמן?) |

### עתידי (Phase 2)

| נושא | מתי |
|------|-----|
| **מדדי Paper Trading** | Decision Consistency, Blocked Loss Rate, Regret — מדידת אמינות התנהגותית בזמן אמת |
| **Dual-Track ML** | Anchor (5–7y) + Scout (12–18mo) — רק אחרי שיש נתוני Paper Trading אמיתיים |

---

## חלק א׳ — מה עשינו עד כה

### 1.1 רקע הבעיה

- **Stat Core בלבד** (ARIMA, GARCH, Rule Engine) הגיע לדיוק ~40% בחיזוי כיוון — מתחת לאקראי.
- **Validation 40 תאריכים:** Stat Core 65% (daily), Stat+ML 83% (6 החלטות משמעותיות) — ML שיפר כשהחמיר את הפילטר.
- **המסקנה:** המעבר מ-Accuracy (מדד ML) ל-**Sharpe/Drawdown** (מדדי כסף) — התוכנית המרכזית.

### 1.2 מה יישמנו

| # | רכיב | תיאור |
|---|------|--------|
| 1 | **Calibration** | `scripts/calibrate_ml_threshold.py` — Point-in-time, min 20 trades, `check_cross_asset_alignment_from_series` עם SP/VIX נקודתי, grid 0.52–0.70 |
| 2 | **BacktestEngine + ML** | `backtesting/engine.py` — `use_ml`, `ml_threshold`, Pre-compute תחזיות LSTM, `by_regime` (Sharpe/Drawdown לכל regime) |
| 3 | **עלויות** | `commission_bps=5`, `slippage_bps=3` — round-trip 0.16% בעת כניסה |
| 4 | **run_backtest_with_ml.py** | Stat vs Stat+ML, Decision Density (Trades/Year, Avg Days, Avg Return/Trade), Threshold Stability (`--stability`), `--save-equity`, `--plot` |
| 5 | **API** | `ML_THRESHOLD` מ־env — ברירת מחדל מעודכנת לאחר calibration |
| 6 | **yahoo_finance** | Retry logic, המרה מ-period ל־start/end dates — שיפור עמידות |
| 7 | **TRADING_READINESS_PLAN.md** | תוכנית מוכנות למסחר — Calibration, Backtest, בדיקות סיכון, קו אדום |

### 1.3 Commits

```
58a748d  FRED yield_curve + shift(1), LSTM retrain, ML daily-only, point-in-time validation
5141830  Trading readiness: Calibration, Backtest+ML, costs, TRADING_READINESS_PLAN
```

---

## חלק ב׳ — תוצאות הבדיקות

### 2.1 Backtest — AAPL 3 שנים (עם עלויות 5+3 bps)

| מדד | Stat Core בלבד | Stat + ML (threshold 0.60) |
|-----|----------------|----------------------------|
| **Sharpe** | 1.731 | 1.388 |
| **Max Drawdown** | -11.3% | **-4.0%** |
| **Total Return** | 51.9% | 28.2% |
| **N Trades** | 153 | 75 |
| **Hit Rate** | 58.2% | 56.0% |
| **Exposure** | 32.3% | 15.9% |

### 2.2 Regime Breakdown

| Regime | Stat Core: Sharpe / DD / Trades | Stat+ML: Sharpe / DD / Trades |
|--------|---------------------------------|------------------------------|
| **trend** | 2.61 / -6.5% / 60 | 2.27 / -2.4% / 30 |
| **mean_reverting** | 1.99 / -6.0% / 93 | 1.41 / -4.0% / 45 |
| **high_volatility** | 0 / 0% / 0 | 0 / 0% / 0 |

### 2.3 ניתוח קצר

| ממצא | משמעות |
|------|--------|
| **ML כמסנן סיכון** | Max DD יורד מ־11.3% ל־4% — צמצום ברור של Drawdown |
| **Exposure נמוך** | 15.9% — מתחת לסף 20% שבתוכנית (אזהרה: "מערכת רדומה") |
| **Regime** | אין regime קטסטרופלי — trend ו-mean_reverting עם Sharpe חיובי |
| **קו אדום** | Max DD נמוך ב־≥15% ✅ | Exposure ≥ 20% ⚠️ | Sharpe ≥ Stat ➖ |
| **high_volatility: 0 טריידים** | Rule Engine / ML מזהים שוק "משוגע" ונשארים בחוץ — מנגנון הגנה שעובד |

### 2.4 הטרייד-אוף הקלאסי (Gemini)

| ניצחון | הורדת Max DD מ־11.3% ל־4% — הבדל בין סוחר שישן בלילה לבין סוחר בלחץ |
| מחיר | אובדן ~50% מהתשואה (51%→28%), Exposure צונח — ML שמרן קיצוני |
| תמצית | ML מעדיף "לשתוק" מאשר לטעות. Stat Core "יעיל" יותר (Sharpe), אבל ML הופך לאסטרטגיה "Investable" לסובלנות הפסד נמוכה |

### 2.5 הערכה: מספיק חזק למסחר?

- **Paper Trading:** כן — Sharpe חיובי, Drawdown נמוך, Regime יציב.
- **כסף אמיתי:** לא מספיק עדיין — צריך Paper trading 3–6 חודשים, Threshold Stability, עדכון מסמכים.

---

## חלק ג׳ — תוכנית ההמשך

### 3.1 מה נשאר לפי TRADING_READINESS_PLAN

| # | משימה | סוג | סטטוס |
|---|--------|-----|--------|
| 1 | **הרצת Calibration** | הרצה | לא בוצע — לקבל סף מומלץ, לעדכן ML_THRESHOLD |
| 2 | **Threshold Stability** | הרצה | `--stability` — טבלה 6 ספים (0.52–0.65), חיפוש Plateau |
| 3 | **Error Type Analysis** | פיתוח | **עדיפות גבוהה** — האם ML סינן טריידים מפסידים (מעולה) או אקראי? |
| 4 | **עדכון מסמכים** | תיעוד | STATUS_AND_RECOMMENDATIONS, IMPROVEMENTS_PROPOSAL — לשלב תוצאות |

**דגש (Gemini):** בחיפוש Plateau — לא רק הסף עם Sharpe מקסימלי, אלא **טווח** שבו התוצאות יציבות. אם 0.58 מעולה ו־0.62 קורס → overfitting. אם כל הטווח דומה → מודל רובסטי.

### 3.2 סדר ביצוע מתוכנן

```
1. הרצת Calibration
   → python scripts/calibrate_ml_threshold.py
   → אם הסף ≠ 0.6 — עדכון .env: ML_THRESHOLD=X.XX

2. Threshold Stability
   → python scripts/run_backtest_with_ml.py --period 3y --stability
   → בדיקה: האם 0.58 / 0.60 / 0.62 נותנים ביצועים דומים

3. עדכון מסמכים
   → STATUS_AND_RECOMMENDATIONS — הוספת סעיף תוצאות Backtest + ML
   → IMPROVEMENTS_PROPOSAL — עדכון בהתאם

4. Error Type Analysis (עדיפות גבוהה)
   → המערכת מסננת ~50% מטריידי Stat Core — חייב לדעת: סיננה מפסידים או אקראי?
   → False Positive (כניסה להפסד) vs False Negative (פספוס רווח)
```

### 3.3 מה לא לעשות (חלק י׳ בתוכנית)

- ❌ לא להוסיף Features
- ❌ לא להוסיף Short
- ❌ לא לשנות Architecture
- ❌ לא לאמן מחדש LSTM

**זה שלב הוכחה, לא שלב פיתוח.**

---

## חלק ד׳ — מה חסר ל-"כן" (מסחר אמיתי)?

**מצב נוכחי:** Stat-Led with ML Safeguard, סף 0.80 — **"להפעיל במצב שמרני"**. לא "מכונת כסף", אלא אסטרטגיה סולידית.

### 4.1 משוכות להמשך

| משוכה | תיאור | מאמץ | עדיפות |
|-------|--------|------|--------|
| **Alpha Decay** | LSTM אומן על היסטוריה — שחיקה בתנאי 2025–2026 | בינוני | גבוהה |
| **Walk-Forward Optimization** | אימון מחדש כל רבעון (Rolling window) — לימוד דינמיקה עדכנית | גבוה | קריטי |
| **Positive Alpha** | ML יודע למצוא טריידים ש-Stat Core מפספס, לא רק לסנן | גבוה | לטווח ארוך |

### 4.2 דעת מערכת

- **Alpha Decay:** אמת — המודל "רואה" 2022 ולא 2025. Negative Filter מפחית נזק אך לא פותר את השחיקה.
- **Walk-Forward:** הכרחי למסחר רציף. ללא refit תקופתי, ה-ML הופך ל-anchor.
- **Positive Alpha:** כרגע ML = מסנן. אידיאלי: ML גם מזהה הזדמנויות שהסטט מפספס. דורש ארכיטקטורה אחרת (לא רק P_down).

### 4.3 סדר פעולה מומלץ

1. **עכשיו:** Paper Trading 3–6 חודשים עם Negative Filter @ 0.80.
2. **Walk-Forward:** `scripts/walk_forward_retrain.py` — retrain LSTM כל רבעון. ראה נספח.
3. **Q3+:** בחינת Positive Alpha — האם ML יכול להוסיף טריידים (לא רק לחסום).

---

## חלק ה׳ — מסמכי ייחוס

| מסמך | תפקיד |
|------|--------|
| **ALGORITHM_SPEC.md** | מפרט אלגוריתם: כל מרכיבים ופרמטרים |
| **RESULTS_SUMMARY.md** | סיכום מרוכז של כל התוצאות |
| **HEDGE_FUNDS_ANALYSIS_AND_ROADMAP.md** | ניתוח Renaissance/Citadel/Two Sigma + תוכנית שיפור |
| **storage/backtest_runs.json** | היסטוריית הרצות (שמירה אוטומטית) |
| **TRADING_READINESS_PLAN.md** | תוכנית מוכנות למסחר |
| **ROADMAP_V2.md** | תכנון כללי |
| **IMPROVEMENTS_PROPOSAL.md** | שיפורים מפורטים |
| **STATUS_AND_RECOMMENDATIONS.md** | ניתוח בעיה והמלצות |
| **PROGRESS_AND_NEXT_STEPS.md** (זה) | התקדמות, תוצאות והמשך |

---

## נספח — פקודות הרצה

```bash
# Calibration (כ־2 דקות)
python scripts/calibrate_ml_threshold.py

# Backtest Stat vs Stat+ML (default: daily, Negative Filter @ 0.80)
python scripts/run_backtest_with_ml.py --period 3y

# Backtest weekly / regime (Stat only — ML יומי בלבד)
python scripts/run_backtest_with_ml.py --period 5y --horizon weekly
python scripts/run_backtest_with_ml.py --period 6y --horizon regime_outlook

# Validation — daily + weekly + regime (תוצאות לכל horizon)
python scripts/run_validation_with_ml.py

# Disaster threshold stability (0.75–0.85)
python scripts/run_backtest_with_ml.py --period 2y --stability

# שמירת Equity Curve + גרף
python scripts/run_backtest_with_ml.py --period 3y --save-equity equity.csv --plot

# Walk-Forward Retrain (quarterly) — combat Alpha Decay
python scripts/walk_forward_retrain.py

# Check if model stale (older than 90 days)
python scripts/walk_forward_retrain.py --check

# Restore old model after bad retrain (e.g. DD 18% instead of 12%)
python scripts/walk_forward_retrain.py --restore

# Custom window / end date
python scripts/walk_forward_retrain.py --period 5y --end-date 2025-12-31
```

### הגדרות ייצור (Production) — Success Config (lock 0.80)

| משתנה | ערך | תיאור |
|-------|-----|--------|
| `ML_NEGATIVE_FILTER_THRESHOLD` | **0.80** | סף P(down) — חוסם טרייד רק כש־P(down) > 0.80 (Success lock) |
| מודל פעיל | `storage/lstm_model.pt` | מודל היציב (lookback 40) — Sharpe 0.49, DD 12%, Exposure 45% |
| גיבוי | `lstm_model_backup.pt` | גיבוי לפני retrain; `--restore` מחזיר את ה־Success config |

### איך להגיע ל-Hit Rate ~61–64% (Legacy AND)

ה־**61.4%** הושגו ב־**Legacy AND** — רק כשהסטט נותן Edge **וגם** ה-ML מחזיר P(up) ≥ 0.60. זה מסנן הרבה טריידים (70 במקום 153), אבל משאיר בעיקר טריידים חזקים.

| מדד | Stat Core | Stat+ML (Legacy AND) |
|-----|-----------|----------------------|
| **Hit Rate** | 58.2% | **61.4%** |
| **Sharpe** | 1.73 | **2.12** |
| **Max DD** | -11.3% | **-3.6%** |
| **N Trades** | 153 | 70 |
| **Exposure** | 32.3% | 14.8% |

**הרצה:**
```bash
python scripts/run_backtest_with_ml.py --period 3y --no-negative-filter
```

`--no-negative-filter` = מצב Legacy AND (P_up ≥ 0.60), במקום Negative Filter (P_down > 0.80).

### שמירת תוצאות ופרמטרים — Run Registry

**שמירה אוטומטית** בכל הרצת backtest ל־`storage/backtest_runs.json`:

```bash
# עם תווית מותאמת
python scripts/run_backtest_with_ml.py --period 3y --no-negative-filter --label legacy_and_61pct
python scripts/run_backtest_with_ml.py --period 3y --label neg_filter_080
```

נשמרים:
- תאריך, תווית
- פרמטרים: symbol, period, mode (negative_filter / legacy_and), threshold, lookback
- תוצאות: Sharpe, Max DD, Hit Rate, Exposure, N Trades

**צפייה ב־runs:**
```bash
# Windows
type storage\backtest_runs.json

# Linux/Mac
cat storage/backtest_runs.json
```

### תזמון (Windows Task Scheduler / Linux cron)
```text
# Linux: 1st of every quarter (Jan, Apr, Jul, Oct)
0 2 1 1,4,7,10 * cd /path/to/SignalFlow && python scripts/walk_forward_retrain.py

# Windows: Task Scheduler — create task, trigger Monthly, Day 1, Run:
#   python C:\path\to\SignalFlow\scripts\walk_forward_retrain.py
```

---

## נספח ב' — לקחי Retrain ו־Model Promotion

### תוצאות Retrain

| מצב | Stat+ML Sharpe | Max DD | Exposure |
|-----|----------------|--------|----------|
| **מודל ישן** (יציב) | 0.49 | -12% | 45% |
| **מודל חדש** (retrain) | 0.31 | -18.2% | 56% |

המודל החדש הפך ל"חותמת גומי" — איבד דיפרנציאציה, כמעט לא מסנן.

### מפרט המודל הישן (היציב)

| פרמטר | ערך | תיאור |
|-------|-----|--------|
| **Lookback** | 60 | חלון זמנים לאחור (במקום 40) |
| **Features** | returns, vix, credit_spread, yield_curve | וקטור קלט מלא |
| **Dropout** | 0.2–0.3 | Regularization |
| **אימון** | 5y, משטרי שוק שונים | פרספקטיבה רחבה |

לאימון עם lookback 60:
```bash
python scripts/walk_forward_retrain.py --lookback 60
```

### מנגנונים שהוספנו

1. **Model Promotion** — מודל חדש מחליף את הישן רק אם Backtest (3y) מציג: Sharpe ≥ 0.49 ו־DD ≤ 12%.
2. **Early Stopping** — עצירה כשהעלאת Val Loss (patience 15).
3. **Regularization** — Dropout 0.3 (במקום 0.2).
4. **Restore** — `--restore` מחזיר מודל וגם `lstm_train_info.json` מהגיבוי.

---

*מסמך סיכום — גרסה 1.0 — SignalFlow — 2026-03*
