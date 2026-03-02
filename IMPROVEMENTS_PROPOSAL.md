# SignalFlow — הצעת שיפורים (Post Phase 2B)

*הבעיה, מה לא מיושם, ורעיונות לשיפור דיוק החיזוי*

---

## 1. הבעיה — מצב נוכחי

### 1.1 תוצאות Validation (40 תאריכים לכל horizon, AAPL)

| Horizon | Stat Core בלבד | Stat + ML (Ensemble) |
|---------|----------------|----------------------|
| **Daily** | 20 decisions, **65%** (13/20) | 6 decisions, **83%** (5/6) |
| **Weekly** | 32 decisions, **50%** (16/32) | 13 decisions, **38%** (5/13) |
| **סה"כ** | 52 decisions, **56%** | 19 decisions, **53%** |

### 1.2 ניתוח

- **Daily:** ה־ML משפר — פילטר מחמיר מוריד החלטות מ־20 ל־6, אך דיוק עולה מ־65% ל־83%.
- **Weekly:** ה־ML מזיק — המודל אומן על daily, ולא מתאים ל־weekly.
- **הבעיה המרכזית:** חיזוי כיוון בשוק הוא **קשה מאוד**. התקרה הטבעית (price/volume בלבד) קרובה ל־~50%.

### 1.3 מה ה־ROADMAP כבר מגדיר

- **"מתי לא לפעול"** — No Edge חוסם רוב ההחלטות.
- **מדדי הצלחה:** Sharpe, Drawdown — לא רק Accuracy.
- **Precision:** דיוק כשסוחרים, לא דיוק על כל התחזיות.

---

## 2. מה לא מיושם עדיין (לפי ROADMAP)

| רכיב | שלב | פוטנציאל שיפור |
|------|-----|-----------------|
| **Put/Call Ratio** | Phase 2A | סנטימנט אופציות — מידע חיצוני ל־price/volume |
| **Yield Curve (T10Y2Y)** | — | ✔ הושלם — FRED, shift(1), LSTM |
| **Feature Importance (SHAP)** | Phase 2B/2C | זיהוי והסרת features שמוסיפים רעש |
| **LSTM נפרד ל־Weekly** | — | ה־LSTM הנוכחי אומן על daily בלבד |
| **Threshold מותאם** | Phase 2B | הרצת calibration ובחירת סף לפי Precision |
| **אימון על יותר נתונים** | — | 10y במקום 5y — יותר דוגמאות ללמידה |

---

## 3. הצעות שיפור מפורטות

### 3.1 הוספת Put/Call Ratio ⭐ עדיפות גבוהה

**הבעיה:** כרגע יש returns, VIX, credit_spread. כולם קשורים למחיר/תנודתיות. Put/Call הוא מדד **סנטימנט** מהשוק — מה משקיעים מצפים.

**הצעה:**  
- לבדוק זמינות: Yahoo (`^CPC` או דומה), CBOE.  
- אם זמין — להוסיף fetcher, ליישר ל־pipeline, ולהוסיף כ־feature ל־LSTM.

**צפוי:** שיפור ביכולת לזהות sentiment לפני תנועות.

---

### 3.2 שינוי הגדרת Labels

**הבעיה:** כרגע `|ret| > 10 bps` → up/down, אחרת flat. גבול שרירותי, רגיש לרעש.

**הצעה:**  
- חלוקה לפי percentiles: 1/3 עליון = up, 1/3 תחתון = down, 1/3 אמצעי = flat.  
- Labels מאוזנים יותר, פחות תלויים ברעש קטן.

---

### 3.3 Class Weights (משקלים ל־Classes)

**הבעיה:** "flat" נפוץ הרבה יותר מ־up/down. המודל נוטה לנבא flat.

**הצעה:**  
- `class_weight="balanced"` ב־CrossEntropy.  
- מפצה על חוסר איזון בין up/down/flat.

---

### 3.4 LSTM נפרד ל־Weekly

**הבעיה:** מודל אחד מאומן על daily. ב־weekly — דיוק יורד (50% → 38%).

**הצעה:**  
- אימון LSTM על weekly data.  
- lookback 20–30 שבועות (במקום 40 ימים).

---

### 3.5 הרצת Calibration ובחירת סף

**הבעיה:** סף 0.6 ברירת מחדל — לא מותאם לנתונים.

**הצעה:**  
- הרצת `python scripts/calibrate_ml_threshold.py`.  
- בחירת סף לפי Precision או Sharpe.  
- עדכון ברירת המחדל ב־API.

---

### 3.6 Feature Importance (SHAP)

**הבעיה:** לא יודעים אם credit_spread או VIX תורמים או מרעישים.

**הצעה:**  
- דו"ח SHAP — תרומת כל feature.  
- הסרה/הקפאה של features חלשים.

---

### 3.7 הגבלת ML ל־Daily בלבד

**הבעיה:** ML עוזר ב־daily (83%) ומזיק ב־weekly (38%).

**הצעה:**  
- ב־API: שימוש ב־ML רק כש־`horizon == "daily"`.  
- ב־weekly/regime — Stat Core בלבד.

---

### 3.8 אימון על 10 שנים

**הבעיה:** 5y לבדיקה — אולי מעט מדי.

**הצעה:**  
- אימון על 10y (כולל 2020).  
- יותר דוגמאות, תקופות שונות — שיפור אפשרי בהכללה.

---

## 4. סיכום — צעדים לפי ROI

| צעד | השקעה | תוחלת שיפור | עדיפות |
|-----|--------|--------------|--------|
| Put/Call (אם זמין) | בינונית | גבוהה | ⭐ ראשון |
| LSTM ייעודי ל־Weekly או ML רק ב־Daily | נמוכה | בינונית | ⭐ שני |
| Calibration + סף מיטבי | נמוכה | בינונית | ⭐ שלישי |
| Class weights | נמוכה | בינונית | רביעי |
| SHAP + הסרת features חלשים | בינונית | משתנה | חמישי |
| Labels לפי percentiles | נמוכה | משתנה | שישי |
| אימון 10y | נמוכה | משתנה | שביעי |

---

## 5. מסמכי ייחוס

- **ROADMAP_V2.md** — תכנון כללי
- **STATUS_AND_RECOMMENDATIONS.md** — הגדרת הבעיה והמלצות
- **PLANNING.md** — ארכיטקטורה מקורית

---

### עדכון: FredFetcher מורחב

- **Yield Curve (T10Y2Y)** — נוסף. פער 10Y-2Y, אינדיקטור מיתון/צמיחה.
- **fetch_macro_data()** — מחזיר DataFrame עם credit_spread + yield_curve.
- **shift(1)** — נתוני FRED ב־Pipeline: ביום T המודל רואה T-1 (מניעת Look-ahead bias).

### עדכון: ML רק ב־Daily + אימון מחדש

- **LSTM אומן מחדש** עם yield_curve, credit_spread, vix, returns (shift(1) על macro).
- **ML רק ב־Daily** — ב־weekly/regime: Stat Core בלבד (ML מזיק ל־weekly).

---

*מסמך זה מתעד את הצעות השיפור לאחר Phase 2B — גרסה 1.1*
