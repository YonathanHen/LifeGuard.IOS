# SignalFlow — תכנון פרויקט מאפס
# Market Decision Support Platform — Complete Planning Document

*או: Probabilistic Market Direction Engine*

---

## 1. מטרת הפרויקט (Project Vision)

**SignalFlow** — **מערכת אחת** שנותנת תמיכה למסחר **יומי / שבועי** (+ Regime Outlook לטווח בינוני — לא "תחזית חודשית").

**מטרה עסקית:** לתת **כיוון צפוי + סיכון צפוי** — כדי לקבל החלטות השקעה מושכלות, לא "ביטחון שגוי".

**עיקרון קריטי:** Time Horizon הוא **ציר ראשון** — לא פרמטר צדדי. הוא מוזרם לכל שכבה.

**עיקרון מפתח:** ML לא מחליט — הוא **תומך**. הסטטיסטיקה והחוקים מקדימים.

**עקרון עמידות:** המערכת תעדיף **לא לפעול** על פני פעולה שגויה — לא תמיד יהיה כיוון, וזה בסדר.

---

## 2. הארכיטקטורה הכללית (High-Level Architecture)

**סדר הזרימה — קריטי:** Regime → Stat → Rules → ML (לא להפך)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     SIGNALFLOW — Market Decision Support                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────┐     ┌─────────────┐                                              │
│  │   FRONTEND  │────▶│  API LAYER  │                                              │
│  │  (Streamlit │     │  (FastAPI)  │                                              │
│  └─────────────┘     └──────┬──────┘                                              │
│                             │                                                     │
│                             ▼                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                    DECISION ENGINE (סדר חשיבות!)                             │ │
│  │                                                                              │ │
│  │  ⓪ REGIME DETECTOR    ① STAT CORE    ② RULE ENGINE    ③ ML LAYER            │ │
│  │  ┌─────────────┐      ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │ │
│  │  │ HMM /       │─────▶│ ARIMA       │▶│ פילטר       │▶│ XGBoost     │       │ │
│  │  │ Clustering  │ לכבות│ GARCH       │ │ Cross-Asset │ │ LSTM        │       │ │
│  │  │ (vol+ret)   │ כיוון│             │ │ confirmation│ │ Ensemble    │       │ │
│  │  │             │ כשאינו │             │ │             │ │             │       │ │
│  │  │ Trend/Mean/ │ רלוונטי│             │ │ SP500 vs VIX│ │             │       │ │
│  │  │ High-Vol    │      │             │ │             │ │             │       │ │
│  │  └─────────────┘      └─────────────┘ └─────────────┘ └─────────────┘       │ │
│  └──────────────────────────────────┬──────────────────────────────────────────┘ │
│                                     │                                              │
│                                     ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │           DATA LAYER (Pipeline + Cross-Asset: SP500, VIX, אג״ח)              │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. מבנה התיקיות (Project Structure)

```
SignalFlow/
│
├── 📄 README.md                 # תיעוד הפרויקט
├── 📄 PLANNING.md               # מסמך תכנון (זה)
├── 📄 requirements.txt         # תלויות Python
├── 📄 .env.example             # משתני סביבה (דוגמה)
│
├── 📁 config/                   # הגדרות
│   ├── settings.py             # הגדרות מרכזיות
│   ├── horizons.yaml           # פרמטרים לפי horizon (resolution, windows, cooldown)
│   └── symbols.yaml            # רשימת מניות/אינדקסים
│
├── 📁 data/                     # שכבת דאטה
│   ├── __init__.py
│   ├── fetchers/               # שליפת דאטה ממקורות חיצוניים
│   │   ├── yahoo_finance.py    # Yahoo Finance API (adjusted close)
│   │   ├── cross_asset.py      # SP500, VIX (ל-Cross-Asset Confirmation)
│   │   └── alpha_vantage.py    # Alpha Vantage (אופציונלי)
│   ├── preprocessing.py        # ניקוי, אימות raw vs adjusted, Z-score filter
│   ├── features.py             # Feature Engineering
│   └── pipeline.py             # Data Pipeline
│
├── 📁 models/                   # שכבת מודלים (Regime → Stat → Rules → ML)
│   ├── __init__.py
│   ├── base.py                 # Base Model Interface
│   ├── regime/                 # ⓪ REGIME DETECTOR (לפני הכל)
│   │   └── detector.py         # RegimeDetector(symbol, horizon) — Horizon-aware
│   ├── stat/                   # ① STAT CORE (חובה)
│   │   ├── arima_model.py      # כיוון — תוחלת תשואה
│   │   └── garch_model.py      # סיכון — תנודתיות
│   ├── rules/                  # ② RULE ENGINE
│   │   ├── engine.py           # האם יש יתרון? פילטר ל-ML
│   │   └── cross_asset.py      # Cross-Asset Confirmation (SP500 vs VIX)
│   ├── ml/                     # ③ ML LAYER (משני בלבד)
│   │   ├── xgboost_model.py
│   │   ├── lstm_model.py
│   │   └── ensemble_model.py
│   └── train.py                # סקריפט אימון (Stat קודם!)
│
├── 📁 api/                      # שכבת API
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── routes/
│   │   ├── predictions.py
│   │   └── health.py
│   └── schemas.py              # Pydantic models
│
├── 📁 dashboard/                # ממשק משתמש (שלב 3) — ראה סעיף 13
│   ├── app.py                  # Streamlit entry
│   ├── components/             # ראה 13.12, 13.15
│   │   ├── status_bar.py
│   │   ├── decision_card.py
│   │   ├── direction_panel.py
│   │   ├── risk_panel.py
│   │   ├── confidence_panel.py
│   │   ├── regime_panel.py
│   │   ├── chart_panel.py
│   │   └── history_table.py
│   └── styles/
│       └── control_room.css
│
├── 📁 backtesting/              # Strategy-Based Backtesting
│   ├── __init__.py
│   └── engine.py               # Sharpe, max drawdown, hit rate מותנה בסיכון
│
├── 📁 scripts/                  # סקריפטים שימושיים
│   ├── train_all.py            # אימון כל המודלים
│   ├── fetch_data.py           # שליפת דאטה
│   └── run_backtest.py
│
├── 📁 storage/                  # אחסון מקומי (אופציונלי)
│   ├── models/                 # מודלים שמורים
│   ├── data/                   # cache דאטה
│   └── backtest_results/
│
└── 📁 tests/                    # טסטים
    ├── test_data.py
    ├── test_models.py
    └── test_api.py
```

---

## 4. שלוש השכבות העיקריות — פירוט

### 4.0 Time Horizon — First-Class Citizen (חובה)

**Horizon אינו "פילטר" או "dropdown בלבד" — הוא בחירת עדשה שמשפיעה על כל השכבות.**

```
Context = { symbol, horizon: "daily" | "weekly" | "regime_outlook" }
```

**"regime_outlook"** — הערכת משטר לטווח בינוני. **לא** חיזוי כיוון חודשי. ראה 4.0.0 למטה.

| שכבה | השפעת Horizon |
|------|---------------|
| Data | Resolution, Rolling windows, איסור "חודשי על דאטה יומי" |
| Regime | משמעות משטר, Cooldown period |
| Stat | פרמטריזציה ARIMA/GARCH |
| Rules | Cross-Asset alignment |
| ML | **יומי+שבועי בלבד**. regime_outlook = ללא ML. |
| UI | המסך **כולו** מתחלף — אסור להשוות Horizons באותו מסך |

### 4.1 שכבת דאטה (Data Layer)

| קומפוננטה | תפקיד |
|-----------|--------|
| **Fetchers** | שליפת מחירים יומיים מ-Yahoo Finance (yfinance) |
| **Preprocessing** | טיפול ב-NaN, איחוד תאריכים, מילוי gaps. **אימות Adjustments** (raw vs adjusted). **Z-score / Fat-Tail Filter** (ראה למטה). |
| **Features** | Stat: returns, volatility. טכני: MA, RSI, MACD (ראה אזהרה למטה) |
| **Pipeline** | אורקסטרציה: Fetch → Preprocess → Features → Output |

**מקורות דאטה:**
- Yahoo Finance (חינם, שלב 1)
- תקופת אימון: מינימום 2–3 שנים

**⚠️ אזהרה — Features טכניים בלבד:**
MA, RSI, MACD, Bollinger הם **נגזרות של אותו מחיר** — אין כאן מידע חדש. ML על זה בלבד לומד קומבינציות של רעש → עובד ב-backtest, נשבר בזמן אמת.

**הרחבה עתידית (Phase 2+):** דאטה חלופית — סנטימנט חדשות, מאקרו — כדי להוסיף **מידע אמיתי** למודלים.

**Cross-Asset (חובה — Phase 2):** SP500, VIX — לא לניבוי, אלא ל־**Cross-Asset Confirmation** (ראה סעיף 4.0.2).

**Yahoo Finance + Adjusted Close — תיקון קריטי:**  
GARCH ו־ARIMA רגישים לאירועים קיצוניים *מלאכותיים*: split, dividend jump, data glitch.

| פעולה | תיאור |
|-------|--------|
| **אימות Adjustments** | בדיקת raw close מול adjusted, זיהוי קפיצות לא סבירות |
| **Z-score / Fat-Tail Filter** | Sanity Filter — לא "feature". אם יום: \|z\| > threshold → להפחית משקל או לסמן period כ־unstable |
| **מטרה** | להגן על Stat Core, לא "להתקן את השוק" |

**Data Resolution לפי Horizon (חובה):**

| Horizon | Data Resolution | Z-score Rolling |
|---------|-----------------|-----------------|
| **יומי** | Daily bars | 20–40 |
| **שבועי** | **Weekly aggregated OHLC** (לא ממוצע!) | 12–26 |
| **regime_outlook** | Monthly bars (להערכת משטר בלבד) | 6–12 |

**❌ אסור:** "לנבא חודשי על דאטה יומי" — יוצר אשליית דיוק.

---

**4.0.0 מדוע לא "חודשי" כחיזוי — ובמקום מה:**

- **תצפיות:** 12/שנה, 120 ב־10 שנים — גבולי לסטטיסטיקה
- **חודשי = משטרים**, לא תחזית — מתחלפים לא יפה, חופפים
- **ביטחון שגוי:** תחזית חודשית משדרת "יציבות" בעוד שחוסר הוודאות גבוה יותר

**פתרון: Regime Outlook** — `market_regime_outlook`, `risk_trend`, `suitability_for_exposure` (Yes/Caution/No). בלי אחוזים, בלי חצים, בלי "יעד לחודש הבא".

---

### 4.0 שכבות עמידות — כשסטטיסטיקה "נשברת"

ARIMA/LSTM/XGBoost כולם לומדים **דפוסים פנימיים של אותו נכס**. כשמבנה השוק משתנה — גם סטטיסטיקה טובה וגם ML טוב מאבדים אחיזה.  
**לכן מוסיפים זווית כיוון נוספת:** לא כדי "לנבא יותר", אלא כדי **לא להיכנס כשלא מבינים מה קורה**.

#### 4.0.1 Regime Detection (מומלץ מאוד)

**למה קריטי?** אותו כיוון:
- עובד נהדר בשוק שקט
- נשבר בשוק משברי
- מטעה בשוק צדדי

**הפתרון:** לפני Stat Core — להבין באיזה **משטר שוק** אנחנו:
- Trend / Mean-Reverting / High-Volatility
- או: Risk-On / Risk-Off

**מימוש:** Hidden Markov Model (HMM) או clustering על volatility + returns.  

**Regime חייב להיות Horizon-aware — לא Regime אחד לכל הטווחים.**

שוק יכול להיות Trend חודשי אך רעש יומי מטורף.

| Horizon | משמעות Regime |
|---------|---------------|
| **יומי** | Noise / Short-term Trend / High-Vol |
| **שבועי** | Swing Trend / Mean Reversion |
| **regime_outlook** | Macro Trend / Risk-On / Risk-Off |

**Forced Cooldown לפי Horizon:**

| Horizon | Cooldown |
|---------|----------|
| יומי | 2–3 ימים |
| שבועי | 1 שבוע |
| regime_outlook | (לא חיזוי — אין Cooldown כבקשת "תחזית") |

אחרת — "רודפים" שינויי משטר שלא רלוונטיים לטווח.

**תפקיד:** לכבות כיוון כשלא רלוונטי — **לא לחזות**, אלא להחליט מתי לא להפעיל.

**Liquidity Gate (חובה — לא מודל נוסף):**  
Regime מזהה *מה* השוק עושה, אך לא *כמה יקר להשתתף*. נזילות משפיעה על spread, slippage, היתכנות האות.

- אם spread יחסי / volume יורד מתחת לסף → **Regime = Tradable = False**
- **Phase 1:** Dollar volume ממוצע **20 ימים** (לא יום אחרון — יציב יותר, פחות רגיש לימים חריגים). סף: 2M$/יום. מונע Slippage.
- לא "משטר חדש" — **כיבוי החלטות**
- מתאים לעיקרון: העדפת אי־פעולה. לא מוסיף ML. לא מסבך.

**Forced Cooldown אחרי Regime Shift:**  
שינוי משטר = נתונים לא יציבים. גם אם האות "נראה טוב" — אינו אמין.

- **Forced Neutral Period** (למשל 3 ימים) אחרי זיהוי שינוי משטר
- **טריגר Cooldown:** רק אם HMM מזהה הסתברות >80% למשטר חדש **במשך יומיים רצופים**. מונע "קיפאון" עקב תנודות קלות של יום אחד.
- במהלך Cooldown: No Edge, אין החלטות
- UI: Countdown קטן "Cooling down: Day 2 / 3", הסבר טקסטואלי רגוע
- הופך את המערכת ל־"מצפון". מונע Overreaction.

#### 4.0.2 Cross-Asset Confirmation (קל, חכם)

**בעיה:** כרגע כל החלטה מבוססת על נכס אחד.  
**בוול סטריט:** "האם נכסים קשורים אומרים אותו דבר?"

דוגמאות:
- מדד ↔ סקטור | מניה ↔ מדד שוק | מניות ↔ VIX
- **אם SP500 ↑ אבל VIX ↑ חזק** → confidence יורד

**שימוש:** Rule Engine נוסף — היגיון שוק בסיסי שמונע טעויות יקרות. **זה לא ML.**

**Cross-Asset Tier 1 (Phase 1–2):** SP500, VIX ✔

**כלל זהב: Cross-Asset חייב להיות באותו קנה זמן — לא "מידע יותר מהר", אלא מידע תואם.**

| Horizon | Cross-Asset חובה |
|---------|------------------|
| **יומי** | VIX יומי |
| **שבועי** | מגמת VIX שבועית |
| **regime_outlook** | VIX חודשי + (עתידית: Yield Curve) |

**Tier 2 (עתידי — לא להכניס הכל בבת אחת):**
- Yield Curve (10y–2y) — רלוונטי יותר לשבועי/חודשי, פחות ליומי
- Credit Spread
- Put/Call Ratio — טוב כ־Fear Indicator, אך בעייתי בזמינות חינמית. מתכננים hook, לא Phase 1.

#### 4.0.3 Direction Stability Score (אופציונלי)

כמה ימים ברצף הכיוון נשאר אותו דבר?
- כיוון UP יום אחד → חלש
- UP 4 ימים רצוף, סטטיסטית יציב → חזק

**עוזר:** למשקיעים שבועיים, מניעת כניסות "רועדות".

---

### 4.2 שכבת מודלים — היררכיה (Regime → Stat → Rules → ML)

**① Stat Core (חובה, קודם לכל):**

| מודל | תפקיד | פלט |
|------|--------|-----|
| **ARIMA** | כיוון — תוחלת תשואה | direction_expectation |
| **GARCH** | סיכון — תנודתיות | volatility_expectation |

**ARIMA — פלט מוגדר (Phase 1):**
- **לא** מספר מדויק (bps) — Rule Engine לא יכול להבדיל "0.03% יומי" מ־רעש
- **כן:** bucket (↑ / → / ↓) + magnitude (Low / Medium)
- Rule Engine יודע: Edge = bucket ברור + magnitude מעל סף

**GARCH חודשי / regime_outlook — להיזהר לא להעמיס:**
- **Low / Medium / High** בלבד
- **בלי** רציפות, בלי scaling ליניארי
- לא "לכייל" מספר שאין לו משמעות — זו הערכת סביבה, לא תחזית

**פרמטריזציה לפי Horizon (אותו מודל, פרמטרים אחרים):**

| Horizon | ARIMA | GARCH |
|---------|-------|-------|
| **יומי** | short memory | risk timing |
| **שבועי** | medium | exposure sizing |
| **regime_outlook** | — (לא חיזוי כיוון) | **Low/Med/High בלבד**, bucket, בלי רציפות |

→ Baseline + Sanity check + **פילטר ל-ML** — ML רץ רק אם יש signal מסטטיסטיקה.

**② Rule Engine:**  
- בודק אם יש יתרון בכלל (ARIMA + GARCH מסכימים? תנאי סיכון עבר?)
- **Cross-Asset Confirmation:** SP500 vs VIX — אם סותרים → confidence יורד
- **Liquidity Gate:** spread/volume מתחת לסף → Tradable = False
- מחליט אם להפעיל ML

**③ ML Layer (משני, לא ראשון):**

| מודל | תפקיד | הערה |
|------|--------|------|
| **XGBoost** | חיזוי כיוון | רק אם עבר פילטר |
| **LSTM** | תבניות טמפורליות | תומך, לא מחליט |
| **Ensemble** | קונצנזוס | agreement בין מודלים |

**כלל קריטי — ML רק יומי ושבועי:**

| Horizon | ML |
|---------|-----|
| יומי | ✔ כן |
| שבועי | ✔ כן (זהיר) |
| **regime_outlook** | **❌ לא** — Regime + Cross-Asset בלבד |

**למה?** regime_outlook = הערכת משטר, לא חיזוי. מעט דגימות. Stat + Regime חזקים מ־LSTM.

**פלט משולב (לא direction + confidence!):**
- `direction_expectation`: כיוון צפוי (או תוחלת תשואה)
- `volatility_expectation`: תנודתיות צפויה (סיכון)
- `risk_score`: ציון סיכון 0–100
- `confidence`: **לא** softmax/proba. **Logical AND** — גורם שלילי אחד → confidence נופל:
  - נוסחה: `Confidence = (Stat_Sign ∩ Regime_Stability) × CrossAsset_Alignment`
  - אין "פיצוי" בין גורמים. אין soft probabilities שמרגיעות שווא.
- `direction_stability_score`: (אופציונלי) כמה ימים ברצף אותו כיוון — UP 4 ימים = חזק, 1 יום = חלש

---

### 4.3 שכבת API (API Layer)

| Endpoint | תיאור |
|----------|--------|
| `GET /health` | בדיקת תקינות |
| `GET /predict/{symbol}?horizon=daily` | תחזית — horizon: daily / weekly / regime_outlook |
| `GET /predictions` | תחזיות לכל המניות (אופציונלי) |
| `POST /train` | טריגר אימון (אופציונלי, admin) |

---

## 5. זרימת העבודה (Workflow)

### 5.1 אימון ראשוני (סדר נכון!)
```
1. fetch_data.py   → שולף היסטוריה (3–5 שנים) + Cross-Asset (SP500, VIX)
2. train.py       → מאמן Regime Detector (HMM/clustering) על vol+returns
3. train.py       → מאמן ARIMA + GARCH (Stat Core)
4. train.py       → בודק baseline, sanity check
5. train.py       → רק אז: XGBoost, LSTM, Ensemble (אם יש יתרון)
6. שמירה ל-storage/models/
```

### 5.2 Inference (בקשת תחזית)
```
1. משתמש → API: GET /predict/AAPL?horizon=daily  (או weekly / monthly)
2. Context = { symbol: AAPL, horizon: daily }
3. API → Data: שליפת דאטה **בהרזולוציה תואמת** + Cross-Asset (SP500, VIX)
3. Data → Features
4. Regime Detector → Trend/Mean/High-Vol? אם לא רלוונטי → כבה כיוון
5. Stat Core (ARIMA, GARCH) → direction_expectation, volatility_expectation
6. Rule Engine → פילטר + Cross-Asset (SP500↑ אך VIX↑↑ → confidence יורד)
7. אם כן → ML (XGBoost, LSTM) → תומך
8. Direction Stability Score (ימים רצופים באותו כיוון)
9. Confidence = agreement + יציבות + Cross-Asset
10. API → משתמש: { direction_expectation, volatility_expectation, risk_score, regime }
```

### 5.3 אימון מחדש (שבועי)
```
Cron/ scheduled job:
- שליפת דאטה חדשה
- אימון מחדש עם Time-Series CV
- החלפת מודלים
```

---

## 5.4 Backtesting — Strategy-Based (לא Accuracy!)

**❌ לא:** accuracy, precision, recall — מטעה ומסוכן.

**✅ כן:**
| מדד | מטרה |
|-----|------|
| **Max Drawdown** | כמה הירידה המקסימלית? |
| **Sharpe Ratio** | תשואה מסתגלת לסיכון |
| **Hit rate מותנה בסיכון** | כשהסיכון נמוך — מה % ההצלחה? |
| **Performance בתקופות רעות** | 2008, 2020 — איך המודל מתנהג? |

Backtesting חייב לשקף **אסטרטגיית מסחר** — לא רק "המודל ניחש נכון".

---

## 6. לוח זמנים לפיתוח (Development Phases)

### Phase 1 — Stat Core + MVP (2–3 שבועות)
- [ ] מבנה פרויקט + requirements
- [ ] Data: Yahoo fetcher + preprocessing (returns, volatility)
- [ ] **Stat Core: ARIMA + GARCH** (חובה — קודם!)
- [ ] Rule Engine בסיסי (פילטר)
- [ ] API: FastAPI + endpoint predict
- [ ] פלט: direction_expectation, volatility_expectation, risk_score
- [ ] **Backtesting Strategy-Based** (Sharpe, max drawdown)

### Phase 2 — עמידות + ML (2 שבועות)
- [ ] **Regime Detector** (HMM / clustering)
- [ ] **Cross-Asset Confirmation** (SP500, VIX fetcher + Rule Engine)
- [ ] Model: XGBoost (רק אחרי Stat עובד)
- [ ] Model: LSTM
- [ ] Ensemble + Confidence = agreement + יציבות + Cross-Asset
- [ ] **Direction Stability Score** (אופציונלי)
- [ ] תחזית שבועית
- [ ] Hit rate מותנה בסיכון

### Phase 3 — Production (2 שבועות)
- [ ] דשבורד מלא (Streamlit)
- [ ] אימון מחדש אוטומטי
- [ ] ניטור ולוגים
- [ ] Performance בתקופות רעות — validation

---

## 7. טכנולוגיות (Tech Stack)

| תחום | טכנולוגיה |
|------|-----------|
| **Language** | Python 3.10+ |
| **Data** | pandas, numpy, yfinance |
| **Stat Core** | statsmodels (ARIMA, GARCH) |
| **Regime Detection** | hmmlearn (HMM) או sklearn (clustering) |
| **ML** | scikit-learn, xgboost, PyTorch (LSTM) |
| **API** | FastAPI |
| **Dashboard** | Streamlit |
| **Storage** | קבצים (pickle/joblib) או SQLite |
| **Env** | python-dotenv |

---

## 8. דרישות מערכת

- Python 3.10+
- ~2GB RAM לאימון
- אינטרנט לשליפת דאטה
- (אופציונלי) GPU ללSTM — אך אפשר גם CPU

---

## 9. סיכום — מה נבנה

1. **Data Pipeline** — שליפה, עיבוד, returns + volatility, **Cross-Asset (SP500, VIX)**
2. **Regime Detector (לפני הכל)** — HMM/clustering: לכבות כיוון כשלא רלוונטי
3. **Stat Core** — ARIMA, GARCH: baseline, sanity check, פילטר
4. **Rule Engine** — פילטר + **Cross-Asset Confirmation**
5. **ML Layer (משני)** — XGBoost, LSTM, Ensemble — תומכים, לא מחליטים
6. **Direction Stability Score** — ימים רצופים באותו כיוון
7. **API** — FastAPI: direction_expectation, volatility_expectation, risk_score, regime
8. **Backtesting** — Strategy-Based: Sharpe, max drawdown, hit rate מותנה בסיכון
9. **Confidence** — agreement + יציבות + Cross-Asset, לא softmax

**עם Regime + Cross-Asset → מערכת ברמה מוסדית קטנה.**

---

## 10. עקרונות מתודולוגיים (חשוב!)

| עקרון | משמעות |
|-------|--------|
| **Regime לפני Stat** | להבין באיזה משטר שוק — לכבות כיוון כשלא רלוונטי |
| **Stat לפני ML** | אף אחד בוול סטריט לא מתחיל מ-XGBoost |
| **הפרדת כיוון וסיכון** | direction_expectation ≠ volatility_expectation |
| **ML תומך, לא מחליט** | הוא Layer משני אחרי פילטר |
| **Confidence = Logical AND** | (Stat ∩ Regime) × CrossAsset. גורם שלילי אחד → נופל. לא soft probabilities. |
| **Backtesting = Strategy** | Sharpe, drawdown — לא accuracy |
| **XGBoost/LSTM = כלים** | לא "אלגוריתמים מהוול סטריט" — האסטרטגיה היא איך משלבים + סיכון + חוקים |
| **העדפת אי-פעולה** | לא לפעול עדיף על פעולה שגויה — לא תמיד יהיה כיוון |

---

## 11. מה לא להוסיף (חשוב לא פחות)

| ❌ לא | למה |
|------|-----|
| עוד אינדיקטורים טכניים | מגדילים מורכבות, לא משפרים החלטות |
| עוד מודלי ML | |
| NLP חדשות בשלב הזה | |
| Reinforcement Learning | |
| "חיזוי מחיר מדויק" | |
| חיזוי כיוון חודשי | → Regime Outlook במקום (Risk-On/Off, suitability) |

**כל אלה** — מגדילים מורכבות, לא בהכרח משפרים החלטות.

---

## 12. סרגל הערכה — מתי המערכת "מספיק טובה"?

**כן** — מספיק טוב כדי להתחיל להשקיע על בסיסו, בתנאי אחד:  
**את מקבלת מראש שלא תמיד יהיה כיוון** — והמערכת תעדיף לא לפעול על פני פעולה שגויה.

**עם תוספת:** Regime Detection + Cross-Asset sanity check → **מערכת ברמה מוסדית קטנה**.

---

## 13. Dashboard / UI — מפרט עיצוב (קריטי)

**עקרון־על:** ה־UI משדר **מערכת בקרה**, לא מערכת המלצות.

| לא | כן |
|----|-----|
| אפליקציית מסחר | לוח מחוונים של חדר בקרה |
| TradingView, Robinhood | תחושה של "עצור, תחשוב" |

**אם ה־UI יהיה "יפה מדי" או "מלהיב מדי" — הוא יפגע באיכות ההחלטות.**

**כלל UI קריטי — Horizon Selector:**

| ❌ אסור | ✔ כן |
|---------|------|
| להשוות בין Horizons על אותו מסך ("יומי ↑, שבועי ↓, חודשי ↑↑") | **Selector:** `Horizon: Daily \| Weekly \| Monthly` |
| Cherry-picking — "אבחר את מה שמתאים לי" | **המסך כולו מתחלף לוגית** — Daily / Weekly / Regime Outlook |

בחירת Horizon → **כל** הרכיבים מתאימים עצמם. מונע בלבול ומניפולציה.

---

### 13.1 שורת מצב עליונה (Status Bar) — חובה

**החלק הכי חשוב במסך.** אם אין יתרון — ברור עוד לפני גרפים.

```
נכס: AAPL     טווח: יומי
Regime: High-Volatility
מצב מערכת: ⚠ אין יתרון סטטיסטי
```

או:

```
Regime: Trend
מצב מערכת: ✔ יתרון קיים (מותנה בסיכון)
```

---

### 13.2 כרטיס החלטה מרכזי (Decision Card)

**מרכז המסך. כרטיס אחד בלבד.**

```
כיוון צפוי: ↑ מתון
תוחלת תשואה: +0.18%
תנודתיות צפויה: גבוהה
Risk Score: 64 / 100

הערכת מערכת:
יש כיוון, אך הסיכון גבוה — זהירות
```

| ❌ אסור | ✔ חייב |
|---------|--------|
| BUY / SELL | ניסוח זהיר |
| "צפי מחיר" | הפרדה מוחלטת: כיוון ≠ סיכון |
| אחוזי דיוק | |

---

### 13.3 הפרדה ויזואלית חדה: Direction ≠ Risk

**שני אזורים שונים בעין.** אם קרובים מדי → ביטחון שווא.

| 🔵 Direction (שמאל) | 🔴 Risk (ימין) |
|---------------------|----------------|
| חץ ↑ ↓ → | מד חצי־עגול (Low/Medium/High) |
| תוחלת תשואה | תנודתיות צפויה |
| Direction Stability Score (יציב 4 ימים) | הערה אם הסיכון עולה |

---

### 13.4 Confidence — מוסבר, לא מספר

| ❌ לא | ✔ כן |
|------|------|
| Confidence: 71% | Confidence: בינוני |
| | **מבוסס על:** |
| | ✔ הסכמה בין ARIMA + ML |
| | ✔ יציבות כיוון 3 ימים |
| | ✖ VIX עולה — Cross-Asset שלילי |

**זה לא softmax — זה פירוט.**

---

### 13.5 Regime — גלוי, לא חבוי

```
Market Regime: High Volatility
המשמעות: כיוונים פחות אמינים, סיכון גבוה
```

✔ מחנך | ✔ מונע over-trading

---

### 13.6 גרפים — מינימום הכרחי

| ברירת מחדל | ❌ אסור |
|------------|---------|
| גרף מחיר פשוט | 10 אינדיקטורים |
| Band תנודתיות (GARCH) | צבעים צעקניים |
| אזורים אפורים = "No Trade Zone" | Candles אגרסיביים |

**גרף = תמיכה להחלטה, לא ההחלטה.**

---

### 13.7 היסטוריית החלטות — קריטי למשמעת

טבלה פשוטה — **מונעת "זיכרון סלקטיבי"**:

| תאריך | Regime | כיוון | Risk | החלטת מערכת |
|-------|--------|-------|------|--------------|
| 12/3 | Trend | ↑ | נמוך | מותר לשקול |
| 13/3 | High-Vol | → | גבוה | הימנעות |
| 14/3 | Trend | ↑ | בינוני | מותר לשקול |

---

### 13.8 עיצוב (Visual Language)

| אלמנט | מפרט |
|-------|------|
| צבעים | אפור, כחול כהה, ירוק כהה — רגועים |
| אדום | **רק** לסיכון גבוה |
| ריווח | הרבה whitespace |
| פונט | פשוט, קריא |
| תחושה | **מערכת בקרה תעשייתית** — לא אפליקציית מסחר |

---

### 13.9 מה אסור להציג — גם אם מפתה

| ❌ אסור | למה |
|---------|-----|
| Accuracy | שובר משמעת |
| "אם היית משקיעה X" | |
| גרף Equity בזמן אמת | |
| אחוזי הצלחה כלליים | |
| "מודל מנצח" | |

---

### 13.10 משפט חובה (למטה, שקט)

```
המערכת מספקת תמיכה הסתברותית בלבד. ייתכן שלא יהיה כיוון.
```

**חשוב לך — לא רק משפטית.**

---

### 13.11 Wireframe טקסטואלי מדויק — מסך ראשי (MVP)

**מה שרואים בעין — מלמעלה למטה:**

```
┌──────────────────────────────────────────────────────────────┐
│ SignalFlow — Market Decision Support                          │
│                                                              │
│ Symbol: AAPL        Horizon: Daily        Updated: 14:32     │
│ Regime: Trend       System Status: ✔ Statistical Edge        │
└──────────────────────────────────────────────────────────────┘
⬆️ StatusBar — תמיד גלוי, לא ניתן להסתרה

┌──────────────────────────────────────────────────────────────┐
│                       DECISION CARD                           │
│                                                              │
│ Direction Expectation:   ↑  Moderate                          │
│ Expected Return:         +0.18%                               │
│                                                              │
│ Volatility Expectation:  High                                 │
│ Risk Score:              64 / 100                             │
│                                                              │
│ System Assessment:                                            │
│ Direction exists, but risk is elevated.                        │
│ Consider caution or reduced exposure.                          │
└──────────────────────────────────────────────────────────────┘
⬆️ כרטיס אחד. אין כפתורי פעולה.

┌───────────────────────────────┐   ┌─────────────────────────┐
│ Direction Details              │   │ Risk Details             │
│-------------------------------│   │--------------------------│
│ Stability: 4 consecutive days │   │ Volatility trend: Rising │
│ Agreement: Stat + ML aligned   │   │ Regime impact: Moderate  │
└───────────────────────────────┘   └─────────────────────────┘
⬆️ הפרדה ויזואלית חדה בין כיוון לסיכון

┌──────────────────────────────────────────────────────────────┐
│ Confidence Breakdown                                          │
│--------------------------------------------------------------│
│ ✔ ARIMA & GARCH aligned                                       │
│ ✔ ML ensemble agrees with direction                           │
│ ✔ Direction stability above threshold                         │
│ ✖ VIX rising — cross-asset confirmation weakened              │
│                                                              │
│ Overall Confidence: Medium                                     │
└──────────────────────────────────────────────────────────────┘
⬆️ Confidence מוסבר — לא מספר

┌──────────────────────────────────────────────────────────────┐
│ Market Context (Regime Explanation)                            │
│--------------------------------------------------------------│
│ Current regime: Trend                                         │
│ Interpretation: Directional signals are more reliable,        │
│ but risk control remains essential.                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Price & Volatility Overview                                   │
│--------------------------------------------------------------│
│ [ Line chart: price ]                                         │
│ [ Volatility band (GARCH) ]                                   │
│ [ Grey zones: no-trade periods ]                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Recent System Decisions                                       │
│--------------------------------------------------------------│
│ Date       Regime     Direction   Risk   System Decision      │
│ 11/03      Trend      ↑           Low    Consider Entry      │
│ 12/03      High-Vol   →           High   Avoid                │
│ 13/03      Trend      ↑           Medium Consider Entry      │
└──────────────────────────────────────────────────────────────┘

*This system provides probabilistic decision support.
 No market direction is guaranteed.*
```

---

### 13.12 פירוק לקומפוננטות (Streamlit)

| קומפוננטה | אחריות | Props / Input |
|------------|--------|----------------|
| **StatusBar** | Symbol, Horizon, Regime, System Status (Edge / No Edge / **Cooldown**). **אם No Edge → opacity נמוך.** Cooldown: "Cooling down: Day 2/3" | symbol, horizon, regime, has_edge, cooldown_day, cooldown_total, updated_at |
| **DecisionCard** | כיוון, תשואה, תנודתיות, risk_score, הערכת מערכת. **אסור:** BUY/SELL, price target | direction_expectation, expected_return, volatility_expectation, risk_score, system_assessment |
| **DirectionPanel** | פרטי כיוון — יציבות, הסכמה | expected_return, direction_stability_score, model_agreement |
| **RiskPanel** | פרטי סיכון | volatility_expectation, regime, risk_score |
| **ConfidencePanel** | רשימת גורמים, **לא מספר**. `[(factor, bool), ...]` | factors: [("ARIMA aligned", True), ("ML agreement", True), ("Cross-Asset VIX", False)] |
| **RegimePanel** | חינוך המשתמשת — הסבר Regime | regime, interpretation |
| **ChartPanel** | מחיר + GARCH band + No-Trade zones | price_series, volatility_band, no_trade_zones |
| **HistoryTable** | טבלת החלטות — פשוטה, בלי פילטרים מתוחכמים | decisions: [{date, regime, direction, risk, decision}] |

---

### 13.13 ביקורת UX — איפה משתמשת תטעה, ואיך מונעים

| טעות | פתרון |
|------|--------|
| **#1 "יש חץ למעלה → נכנסים"** | חץ תמיד מופיע עם Risk. ניסוח טקסטואלי זהיר. **אין כפתור פעולה.** |
| **#2 התעלמות מ-Regime** | Regime תמיד ב-StatusBar. הסבר טקסטואלי קצר מתחת. |
| **#3 אמון יתר ב-Confidence** | אין מספר. יש פירוק לגורמים. גורמים שליליים **בולטים ויזואלית**. |
| **#4 Over-trading** | "No Edge" מכבה את המסך (opacity). History מראה ימים של **הימנעות כהחלטה תקינה**. |
| **#5 זיכרון סלקטיבי ("המערכת תמיד צדקה")** | טבלת החלטות. **אין גרף רווחים נוצץ.** |

---

### 13.14 כלל "No Edge" — התנהגות מסך

**אם System Status = No Edge:**
- StatusBar נשאר מלא (ברור)
- **שאר המסך:** opacity נמוך (למשל 0.5)
- DecisionCard מציג: "אין יתרון סטטיסטי — הימנעות"

**Forced Cooldown Mode (אחרי Regime Shift):**
- StatusBar מציג: "Cooling down: Day 2 / 3"
- הסבר: "שינוי משטר זוהה. נתונים לא יציבים — המתנה X ימים."
- אותו התנהגות כמו No Edge — מסך כבוי

---

### 13.15 מבנה קוד מומלץ (dashboard/)

```
dashboard/
├── app.py                 # Streamlit entry — סידור רכיבים
├── components/
│   ├── status_bar.py      # StatusBar
│   ├── decision_card.py   # DecisionCard
│   ├── direction_panel.py # DirectionPanel
│   ├── risk_panel.py      # RiskPanel
│   ├── confidence_panel.py# ConfidencePanel
│   ├── regime_panel.py    # RegimePanel
│   ├── chart_panel.py    # ChartPanel
│   └── history_table.py   # HistoryTable
└── styles/
    └── control_room.css   # צבעים, spacing — תעשייתי
```

---

## 14. Actionable — מה לאמץ מיד, מה לדחות

**✔ לאמץ מיד (Phase 1–2):**
| פריט | מטרה |
|------|------|
| Z-score / Fat-Tail Filter (Rolling לפי Horizon) | מגן על Stat Core מקפיצות מלאכותיות |
| Forced No-Edge אחרי Regime Shift | Cooldown — מונע Overreaction |
| Confidence כ־Logical AND | גורם שלילי אחד → confidence נופל |
| Liquidity Gate (מחזור 20 ימים ממוצע ≥ 2M$/יום) | Dollar volume ממוצע 20 ימים. מונע Slippage. |
| אימות Adjustments (raw vs adjusted) | זיהוי split, dividend, glitch |

**⏳ לתכנן, לדחות (לא Phase 1):**
| פריט | סיבה |
|------|------|
| Put/Call Ratio | בעייתי בזמינות חינמית |
| Yield Curve | רלוונטי יותר לשבועי/חודשי |
| Credit Spread | Tier 2 |
| מאקרו כבד | לא להכניס הכל בבת אחת |

**הערות אלה לא סותרות את הארכיטקטורה — הן הופכות אותה לבוגרת יותר.**

---

## 15. מערכת רב־טווחית — סיכום תנאים

**המערכת תומכת יומי + שבועי + regime_outlook:**

| תנאי | משמעות |
|------|--------|
| **Horizon = First-Class** | Context גלובלי שמוזרם לכל שכבה |
| **regime_outlook ≠ חיזוי** | הערכת משטר (Risk-On/Off), suitability — בלי תחזית כיוון |
| **Data resolution תואם** | יומי/שבועי/חודשי (רק ל־regime) |
| **Regime Horizon-aware** | משמעות שונה, Cooldown שונה |
| **Cross-Asset באותו קנה זמן** | VIX בהתאמה |
| **ML רק יומי+שבועי** | regime_outlook = Regime + Cross-Asset בלבד |
| **UI: Selector יחיד** | Daily / Weekly / Regime Outlook — מסך מלא מתחלף |

---

## 16. הערות מימוש (עדכון 3.4)

| נושא | המלצה |
|------|--------|
| **Z-score** | Rolling לפי Horizon: יומי 20–40, שבועי 12–26, חודשי 6–12 |
| **Cooldown trigger** | רק אם HMM >80% למשטר חדש **יומיים רצופים** — מונע קיפאון מרעש |
| **Time Horizon** | VIX יומי ↔ חיזוי יומי. VIX שבועי ↔ חיזוי שבועי |
| **Liquidity Phase 1** | Dollar volume ממוצע 20 ימים ≥ 2M$/יום — יציב יותר מיום אחרון |
| **Horizon בכל שכבה** | Context {symbol, horizon} מוזרם מ־API לכל רכיב |
| **ARIMA פלט** | bucket (↑/→/↓) + magnitude (Low/Med) — לא מספר. Rule Engine צריך Edge ברור. |
| **GARCH regime_outlook** | Low/Med/High בלבד — בלי רציפות, בלי לכייל. |

---

*מסמך תכנון — גרסה 3.6 — SignalFlow Market Decision Support Platform*
