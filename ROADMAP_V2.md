# SignalFlow — מסמך סטטוס ותכנון המשך (גרסה 2)

*מה יש לנו • על פי מה ממשיכים • מפת הדרך*

---

## חלק א׳ — מה יש לנו (הבסיס הקיים)

### 1.1 ארכיטקטורה נוכחית — נשארת ללא שינוי

```
┌─────────────────────────────────────────────────────────────────┐
│  SignalFlow — השלד הקיים (Stat Core + Rule Engine)               │
├─────────────────────────────────────────────────────────────────┤
│  ⓪ Regime Detector (HMM)    → לכבות כיוון כשלא רלוונטי          │
│  ① Stat Core (ARIMA, GARCH) → כיוון + תנודתיות                  │
│  ② Rule Engine              → Edge, Liquidity, Cross-Asset       │
│     Forced Cooldown         → אחרי regime shift                 │
│  API + Dashboard MVP        → GET /predict, StatusBar, Decision  │
│  Backtesting + Validation   → Point-in-Time, Strategy metrics    │
└─────────────────────────────────────────────────────────────────┘
```

**כל זה נשאר.** הוא משמש כ־**first line filter** ו־**מבוגר אחראי**.

### 1.2 תוצאות והבנה

- **אימות Point-in-Time:** ~40% דיוק חיזוי כיוון (daily/weekly) — מתחת לאקראי.
- **המסקנה:** חיזוי כיוון על בסיס price/volume בלבד מגיע ל־**תקרה (~50%)**.
- **הסיבה:** רעש לבן — המודל מחפש דפוסים במערכת סגורה ורועשת.

### 1.3 ערך No-Trade — גם בלי שיפור Accuracy

**גם אם Accuracy לא עולה ל־60%, המערכת עדיין שווה.**  
המטרה: שיפור **Profit Factor** ו־**Sharpe**, לא דיוק בינארי.

דוגמה: אם המערכת מסננת **70%** מהימים כ־No Edge, ובשאר **30%** צודקת ב־**55%** — זהו ניצחון. הימנעות מהפסד = רווח.

### 1.4 עיקרון המשך

> **זה לא שינוי כיוון — זו התבגרות.**  
> השלד נשאר. מה שנוסיף = **חושים חדשים** (External Features + ML Layer) כדי לשבור את התקרה.

---

## חלק ב׳ — כיוון התכנון: שבירת ה-Ceiling

### 2.1 למה External Features שוברים את התקרה?

| סוג מידע | מה נותן |
|----------|---------|
| Price/Volume | בסיס — **כבר יש** |
| Volatility (GARCH, VIX) | תנודתיות — **כבר יש** |
| **סנטימנט (חדשות, סושיאל)** | סיבתיות לתנועות קצרות |
| **מאקרו (CPI, GDP, PMI)** | כיוון כללי (bull/bear) |
| **אופציות (Put/Call, IV)** | ציפיות משקיעים |
| **Yield Curve / Credit** | סנטימנט סיכון |

**External Features = דלק חיצוני.** מוסיפים **סיבתיות**, לא רק מתאם.

### 2.2 ארכיטקטורה מורחבת (התכנית)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  SignalFlow — ארכיטקטורה מורחבת                                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Stat Core + Rule Engine (קיים) — First Line Filter                 │   │
│  │  ARIMA, GARCH, HMM • Edge • Cooldown • Liquidity • Cross-Asset      │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │ No Edge → No Trade (תמיד)               │
│                                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  External Feature Layer (חדש)                                       │   │
│  │  VIX • Put/Call • Credit Spreads • (עתיד: News, CPI)                │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ML / Sequence Layer (חדש)                                          │   │
│  │  LSTM / Bi-LSTM • Input: price + external features                  │   │
│  │  Output: P(up), P(down), P(no_move)                                 │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Decision & Risk Layer                                              │   │
│  │  Trade רק אם: Stat Core Edge AND P(up/down) > 0.6–0.65             │   │
│  │  Logical AND — שניהם חייבים לאשר                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 עקרונות קריטיים

| עקרון | משמעות |
|-------|--------|
| **Stat Core = Filter** | No Edge → No Trade, גם אם ML אומר "כן" |
| **Probabilistic Output** | P(up)/P(down) עם סף 0.6–0.65 — צייד, לא מנחש |
| **Logical AND** | Stat Core ∧ ML ∧ Regime — רק אם כולם תומכים |
| **Data Alignment** | CPI/Options/News → Daily Bar בלי Look-ahead bias |
| **Fallback** | FRED/API למטה → Stat Core Only + אזהרה ב־UI |

---

## חלק ג׳ — Features חיצוניים — סדר עדיפויות

### 3.1 סדר הוספה — FRED קודם (Quick Win)

| שלב | Feature | מקור | זמינות | יתרון |
|-----|---------|------|--------|-------|
| **1** | **Credit Spreads** | FRED (fredapi) | חינם, אמין | סנטימנט מאקרו — **Quick Win** |
| **2** | **VIX** | Yahoo | חינם, כבר יש | תנודתיות, פחד |
| **3** | **Put/Call Ratio** | Yahoo / CBOE | לבדוק — ייתכן scraping | סנטימנט משקיעים |

**המלצה:** להתחיל ב־`data/fetchers/fred_fetcher.py`. FRED חינמי ויציב.

### 3.2 זמינות ועלות

| Feature | מקור | עלות | הערה |
|---------|------|------|------|
| Credit Spreads | FRED (BAMLH0A0HYM2) | חינם | fredapi |
| VIX | Yahoo | חינם | כבר קיים |
| Put/Call | Yahoo / CBOE | לבדוק | CBOE עשוי לדרוש scraping |

### 3.3 Tier 2 — הרחבה

| Feature | מקור | הערה |
|---------|------|------|
| CPI, GDP, PMI | FRED, TradingEconomics | מאקרו — תדירות נמוכה (חודשי) |
| Yield Curve (10y–2y) | FRED | רלוונטי לשבועי/חודשי |

**Tier 3 (לא בשלב ראשון):** News/Sentiment — מורכבות Alignment גבוהה, לא נדרש לפיילוט.

### 3.4 אתגר: Data Alignment ו־Publication Lag

**דוגמה — תאריך ייצור vs תאריך פרסום:**

| Feature | תקופת המדידה | תאריך פרסום טיפוסי | מתי זמין למודל? |
|---------|--------------|---------------------|------------------|
| CPI | ינואר 2024 | 14 בפברואר 2024 | רק מ־14 פברואר |
| GDP Q4 | אוקטובר–דצמבר | 30 בינואר | רק מ־30 ינואר |
| Credit Spreads | יומי | אותו יום | יום $T$ — זמין ב־$T$ |
| Put/Call | יומי | יום המסחר | יום $T$ — זמין ב־$T$ |

**חוק בל יעבור:** ב־Backtest, הנתון של יום $T$ חייב להיות הנתון **שהיה ידוע בפועל** ביום $T$.  
אם CPI ינואר מתפרסם ב־14 בפברואר — המודל **לא** יכול לראות אותו ב־1 בפברואר.

**פתרון:** מנגנון `availability_date` — כל feature יודע מתי הוא הפך זמין. Resampling ל־Daily Bar לפי availability.

---

## חלק ד׳ — Model Architecture

### 4.1 LSTM vs Transformer

| מודל | יתרון | חיסרון | המלצה |
|------|-------|--------|-------|
| **LSTM / Bi-LSTM** | סלחני לסדרות קצרות (~2,500 ימים) | זיכרון מוגבל | **התחל ב־LSTM** |
| Transformer | Long-range dependencies | Overfit מהיר על daily | שלב מאוחר יותר |

**Lookback:** חלון של **20–60 ימים** (חודש עד רבעון). מעבר — המודל "שוכח" או מתבלבל ממגמות ישנות.

### 4.2 פלט המודל

- **לא:** כיוון בינארי (up/down)  
- **כן:** הסתברויות — `P(up)`, `P(down)`, `P(no_move)`

### 4.3 Ensemble ו־Threshold Calibration

```
החלטה סופית = Stat Core Edge AND max(P(up), P(down)) > threshold
```

**הסף לא שרירותי.** Calibration: Grid Search (0.55–0.7) על Validation Set.

**קריטריון בחירה (בחר אחד):**
- **maximize Precision @ Decisions Made** — דיוק כשסוחרים
- **maximize Sharpe Ratio** על subset עם P(up/down) > threshold

מטרה: Sweet Spot — גם אם סוחרים פעם בשבועיים.

---

## חלק ה׳ — Validation & Metrics

### 5.1 Probabilistic Metrics

| מדד | תפקיד |
|-----|--------|
| **Brier Score** | איכות תחזית הסתברותית |
| **Log Loss** | עונש על ביטחון שגוי |

### 5.2 Strategy Metrics

| מדד | תפקיד |
|-----|--------|
| Sharpe Ratio | תשואה מסתגלת לסיכון |
| Max Drawdown | סיכון מקסימלי |
| % Decisions avoided (No Edge) | השפעת הפילטר |
| P&L per trade | ביצועים בפועל |

### 5.3 Out-of-Sample

- תאריכים אקראיים / Rolling window
- כולל תקופות משבר (2008, 2020)
- Stress-test על נכסים שונים

**Rolling window validation** עם retrain כל X ימים (למשל 20–30) — להערכת **Stability** במודל לאורך זמן.

---

## חלק ו׳ — Roadmap מפורט

### Phase 2A — External Features (2–3 שבועות)

| שבוע | Milestone | משימות |
|------|-----------|--------|
| 1 | Fetcher + Alignment | `fred_fetcher.py`, availability date, איחוד ל־Daily Bar |
| 2 | Integration + Test | Pipeline, Put/Call (אם זמין), Fallback מנגנון |

| שלב | משימה | פלט |
|-----|--------|-----|
| 1 | Fetcher: Credit Spreads (FRED) | `data/fetchers/fred_fetcher.py` |
| 2 | Fetcher: Put/Call — אחרי בדיקת זמינות | Series יומית |
| 3 | Alignment: availability date + Daily Bar | DataFrame מאוחד |
| 4 | Integration ב־Pipeline | Features חדשים |
| 5 | Fallback: API למטה → Stat Core Only + UI | מנגנון גמילה |

### Phase 2B — ML Layer (2–3 שבועות) ✔ הושלם

| שבוע | Milestone | משימות |
|------|-----------|--------|
| 1 | LSTM + Features | מודל בסיסי, input pipeline |
| 2 | Ensemble + Calibration | Logical AND, Grid Search threshold |
| 3 | Feature Importance | SHAP — הסרת features חלשים לפני פיילוט |

| שלב | משימה | פלט |
|-----|--------|-----|
| 1 | מודל LSTM (lookback 20–60) | `models/ml/lstm_model.py` ✔ |
| 2 | Input: returns + VIX + Credit (+ P/C) | Pipeline features ✔ |
| 3 | Output: P(up), P(down), P(flat) | Probabilistic ✔ |
| 4 | Ensemble: Stat Core + LSTM | Logical AND ✔ |
| 5 | Threshold Calibration (Precision או Sharpe) | `scripts/calibrate_ml_threshold.py` ✔ |
| 6 | Feature Importance — **להסיר/להקפיא** חלשים לפני פיילוט | (Phase 2C) |

### Phase 2C — Validation & Deployment (1–2 שבועות)

| שבוע | Milestone | משימות |
|------|-----------|--------|
| 1 | Validation + Integration | Brier, Log Loss, Point-in-Time, API |
| 2 | Dashboard + Rollout | UI, Fallback, בדיקות |

| שלב | משימה | פלט |
|-----|--------|-----|
| 1 | Brier Score, Log Loss | Validation script |
| 2 | Point-in-Time עם ML (ללא look-ahead) | השוואה לפני/אחרי |
| 3 | Feature Importance — תרומת Credit/P/C | SHAP report |
| 4 | Integration ב־API | GET /predict מחזיר P(up/down) |
| 5 | Dashboard + Fallback UI | UI מעודכן |

### Phase 2D — אופציונלי (עדיפות נמוכה)

- **XGBoost** — כחלק מה־Ensemble, אם מביא ערך
- **News/Sentiment** — **Tier 3, לא קריטי בשלב ראשון.** מורכבות גבוהה.
- **Transformer** — רק אם LSTM **לא משפר Sharpe ב־>10%** ביחס ל־Stat Core. אחרת — להישאר עם LSTM.

---

## חלק ז׳ — סיכום: על פי מה ממשיכים

### מה יש לנו

- Stat Core (ARIMA, GARCH) + Regime (HMM) + Rule Engine  
- Edge detection, Cooldown, Liquidity, Cross-Asset  
- API, Dashboard MVP, Backtesting, Validation  

### על פי מה מתכננים

1. **שמירה על Stat Core כ־Filter ראשוני** — No Edge = No Trade  
2. **External Features** — FRED (Credit) קודם, Put/Call אחרי בדיקת זמינות  
3. **ML Layer (LSTM)** — פלט הסתברותי, Logical AND עם Stat Core  
4. **Threshold Calibration** — Grid Search על Validation, לא סף שרירותי  
5. **מדדים** — Probabilistic (Brier, Log Loss) + Strategy (Sharpe, Drawdown)  
6. **Data Alignment** — "ידוע ביום T" בלבד, availability date לנתונים בפיגור  
7. **Fallback** — API למטה → Stat Core Only + אזהרה  
8. **Feature Importance** — SHAP/Permutation — להסיר features שמרעישים  

### מסמכי ייחוס

| מסמך | תפקיד |
|------|--------|
| **PLANNING.md** | ארכיטקטורה מקורית, עקרונות |
| **STATUS_AND_RECOMMENDATIONS.md** | ניתוח הבעיה והמלצות |
| **ROADMAP_V2.md** (זה) | סטטוס + תכנון המשך + Roadmap |

---

*מסמך תכנון המשך — גרסה 2.2 — SignalFlow*
