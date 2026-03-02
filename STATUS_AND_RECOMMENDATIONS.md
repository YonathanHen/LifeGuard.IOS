# SignalFlow — סטטוס נוכחי והמלצות להמשך

*מסמך הבעיה והמלצות — עדכון נוכחי*

---

## 0. שינוי כיוון אסטרטגי — Stat-Led with ML Safeguard (מרץ 2025)

המערכת עברה למודל **Stat-Led with ML Safeguard**:

| הישן (AND) | החדש (Negative Filter) |
|------------|-------------------------|
| Trade = Stat Edge **AND** ML P(up) ≥ threshold | Trade = Stat Edge **UNLESS** ML P(down) > disaster_threshold |
| ML חייב לאשר | ML חוסם רק "אסונות" |
| סף P_up (0.6) — Calibration | סף P_down (0.80) — Stability |

**סיבה:** ניתוח Stability ו-Error Type הראה שה-LSTM בעל הטיה שלילית (Pessimistic Bias) — חסם יותר עליות מירידות. המודל החדש מאפשר ל-Stat Core להוביל, ומשתמש ב-ML רק כמסנן אסונות (block when P_down > 0.80).

**תוצאות Backtest (AAPL 2y):** Stat+ML Negative Filter: Sharpe 0.49, Max DD -12% (vs AND: Sharpe -0.55, DD -16%). ה-API ועדכון `.env` עודכנו בהתאם.

---

## 1. מה נבנה עד כה (לפי PLANNING.md)

### 1.1 ארכיטקטורה שהושלמה

| שכבה | מצב | פרטים |
|------|-----|-------|
| **Data Pipeline** | ✔ הושלם | Yahoo Finance, Cross-Asset (SP500, VIX), Z-score filter, dollar volume 20d |
| **Regime Detector** | ✔ הושלם | HMM על (returns, volatility), 3 משטרים, fallback כשאינו מתכנס |
| **Stat Core** | ✔ הושלם | ARIMA (bucket + magnitude), GARCH (volatility bucket) |
| **Rule Engine** | ✔ הושלם | has_edge, liquidity gate, Cross-Asset, Confidence = Logical AND |
| **Forced Cooldown** | ✔ הושלם | אחרי regime shift (2 ימים רצופים >80%), 3/7 ימים לפי horizon |
| **API** | ✔ הושלם | GET /predict/{symbol}?horizon=daily\|weekly\|regime_outlook |
| **Dashboard** | ✔ MVP | StatusBar, DecisionCard, Confidence panel |
| **Backtesting** | ✔ הושלם | Regime + Cross-Asset + Liquidity משולבים |
| **Validation** | ✔ הושלם | Point-in-Time — 15 מדגמים לכל horizon, תאריכים רנדומליים |

### 1.2 מה לא הושלם (לפי PLANNING)

- ML Layer (XGBoost, LSTM, Ensemble)
- train.py מלא
- Dashboard מלא (ChartPanel, HistoryTable, RegimePanel, DirectionPanel, RiskPanel)
- GET /predictions, POST /train
- Direction Stability Score
- Performance בתקופות רעות (2008, 2020)

---

## 2. הגדרת הבעיה — תוצאות האימות

### 2.1 מה בדקנו

מערכת **Point-in-Time Validation**:

- 15 תאריכים רנדומליים לכל horizon (daily, weekly, regime_outlook)
- בלי מידע עתידי — רק נתונים עד לאותו תאריך
- השוואת כיוון החיזוי (up/down) לתשואה בפועל

### 2.2 התוצאות (AAPL, seed=42)

| Horizon | עם כיוון | נכון | שגוי | דיוק |
|---------|----------|------|------|------|
| **Daily** | 10 | 4 | 6 | **40%** |
| **Weekly** | 15 | 6 | 9 | **40%** |
| **Regime Outlook** | 5 | 3 | 2 | 60% |

### 2.3 המשמעות

- **דיוק ~50%** = כמו הטלת מטבע (up/down).
- **40%** = **גרוע מאקראי** — בממוצע עדיף לא להסתמך על הכיוון.
- **60%** (regime_outlook) — מעט טוב מאקראי, אך 5 מדגמים בלבד (לא מובהק סטטיסטית).

### 2.4 ניסוח הבעיה

> **המודלים הסטטיסטיים (ARIMA + GARCH) בשילוב Rule Engine אינם מצליחים לנבא כיוון מחיר יומי/שבועי בצורה שמגיעה לרמת דיוק מעל אקראיות.**

המערכת מציינת כיוון (up/down) רק כשיש "edge" סטטיסטי, אבל גם במקרים האלה — ב־60% מהמקרים הכיוון שגוי.

---

## 3. סיבות אפשריות

### 3.1 קושי מהותי בשוק

- כיוון מחיר לטווח קצר קרוב לרוב ל־**random walk**.
- מידע על returns ו־volatility כבר משתמש ברוב המידע הזמין.
- אין גישה למידע מבחוץ: סנטימנט, חדשות, מאקרו.

### 3.2 מגבלות המודלים

- **ARIMA** — מודל ליניארי, מסתמך על אוטוקורלציה חלשה.
- **GARCH** — מנבא תנודתיות, לא כיוון.
- **HMM** — מזהים משטר, לא מנבאים מחיר.

### 3.3 עיצוב המערכת

- PLANNING מבוסס על **העדפת אי־פעולה**.
- המטרה: **לדעת מתי לא לפעול**, לא "לנבא הכי טוב".
- כיוון מערכתי נדיר — רוב הזמן flat / No Edge.
- עם זאת: כשמתקבל כיוון — הוא עדיין שגוי לעתים קרובות.

---

## 4. המלצות להמשך

### 4.1 המלצה עיקרית — שינוי כיוון

להפסיק לבנות עוד מודלי ML (XGBoost, LSTM) על אותם features, כי צפוי שיפור קטן מאוד.

### 4.2 אפשרות א׳ — התמקדות ב"מתי לא לפעול"

- **מטרה:** להגדיל את אחוז ה־No Edge / flat.
- לשפר את הפילטרים: Regime, Cross-Asset, Liquidity.
- לוודא שהמערכת **נמנעת** כשאין ביטחון.
- **מדידה:** כמה פעמים No Edge חסך החלטה שגויה, לא דיוק חיזוי.

### 4.3 אפשרות ב׳ — הוספת מקורות מידע חדשים (Phase 2+)

לפי PLANNING:

- סנטימנט חדשות
- נתונים מאקרו
- Put/Call Ratio
- Yield Curve
- Credit Spread

רק מידע **חיצוני** ל־price/vol יכול לשפר באמת את יכולת החיזוי.

### 4.4 אפשרות ג׳ — שינוי מדדי הצלחה

- להפסיק למדוד דיוק חיזוי כיוון.
- להתמקד ב־**Sharpe Ratio, Max Drawdown, Hit rate** (כאשר יש edge).
- לבדוק performance ב־crisis periods (2008, 2020).
- להציג ב־UI משפט: "המערכת מספקת תמיכה הסתברותית בלבד. ייתכן שלא יהיה כיוון."

### 4.5 אפשרות ד׳ — השלמת PLANNING כפי שהוא

- להוסיף XGBoost, LSTM, Ensemble.
- לסיים Dashboard מלא, train pipeline.
- **תוחלת שיפור בדיוק:** נמוכה.
- **יתרון:** ארכיטקטורה מלאה, בסיס לשילוב features חדשים בהמשך.

---

## 5. סיכום והמלצה מעשית

| כיוון | השקעה | תוחלת שיפור | המלצה |
|------|--------|--------------|-------|
| **התמקדות בפילטרים (מתי לא לפעול)** | נמוכה | בינונית | ⭐ מומלץ |
| **הוספת נתונים חיצוניים** | גבוהה | גבוהה (אם יש יתרון בנתונים) | לטווח ארוך |
| **שינוי מדדי הצלחה** | נמוכה | — | מומלץ |
| **השלמת ML על אותו דאטה** | בינונית | נמוכה | פחות עדיפות |
| **השלמת Dashboard + Train** | בינונית | חוויית משתמש | שווה אם רוצים מערכת מלאה |

### המלצה מעשית

1. **לא** להשקיע ב־XGBoost/LSTM על אותו דאטה כרגע.
2. **כן** להקשיח את פילטרי "מתי לא לפעול" ולמדוד שיפור ב־No Edge vs שגיאות.
3. **כן** לעדכן את מדדי ההצלחה ל־Strategy-Based (Sharpe, Drawdown).
4. **כן** לסיים את ה־Dashboard וה־train pipeline כדי לקבל מערכת מלאה.
5. **לטווח ארוך:** לתכנן הוספת נתונים חיצוניים (סנטימנט, מאקרו) לפני סיבוב נוסף של מודלים.

---

## 6. עדכון כיוון — מסמך התכנית המפורטת

המסמך **ROADMAP_V2.md** מגדיר את התכנון המעודכן:

- מה יש לנו (הבסיס הקיים)
- כיוון ההמשך: External Features + ML Layer (LSTM)
- Roadmap לפי phases
- Features ראשוניים: Put/Call, Credit Spreads
- ארכיטקטורה: Stat Core + ML ב־Logical AND

**ROADMAP_V2.md** הוא המסמך המנחה לתכנון המערכת מעתה.

### מסמך שיפורים

**IMPROVEMENTS_PROPOSAL.md** — הצעת שיפורים מפורטת (Post Phase 2B):
- הבעיה ותוצאות Validation המעודכנות (40 תאריכים)
- מה לא מיושם (Put/Call, SHAP, LSTM ל־Weekly, Calibration, וכו׳)
- רעיונות לשיפור עם סדר עדיפויות

---

*מסמך זה משקף את המצב הנוכחי — גרסת 1.0 — ומשמש בסיס להחלטות המשך.*
