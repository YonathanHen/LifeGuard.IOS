# SignalFlow — התקדמות, תוצאות ותוכנית המשך

*מסמך סיכום: מה בוצע • תוצאות הבדיקות • כיוון ההמשך*

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

## חלק ד׳ — מסמכי ייחוס

| מסמך | תפקיד |
|------|--------|
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

# Backtest Stat vs Stat+ML
python scripts/run_backtest_with_ml.py --period 3y

# Backtest + Threshold Stability (כ־15 דקות)
python scripts/run_backtest_with_ml.py --period 3y --stability

# שמירת Equity Curve + גרף
python scripts/run_backtest_with_ml.py --period 3y --save-equity equity.csv --plot
```

---

*מסמך סיכום — גרסה 1.0 — SignalFlow — 2026-03*
