# תחקיר: Universal נכסים, מיקוד סקטוריאלי ו-5 אסטרטגיות מובילות

*מחקר מעמיק — איך סטארטפים וקרנות בוחרים נכסים, והאם כדאי להתרכז במניות/סקטורים מסוימים*

---

## 1. האם כדאי להתרכז במניות או סקטורים מסוימים?

### כן — אבל בדרך מתודולוגית

| גישה | יתרונות | חסרונות |
|------|----------|---------|
| **מניה בודדת (AAPL)** | פשטות, מיקוד, קל לאימות | תלות בנכס אחד, סיכון ריכוז |
| **סקטור מסוים (טק, בריאות)** | תזוזות סקטוריאליות ניתנות לניצול | עלול לפספס סקטורים חזקים |
| **Universe רחב (50–100 מניות)** | גיוון, screening, alpha potential | מורכבות, משאבים, overfitting |
| **Sector ETF Rotation** | גיוון אוטומטי, פחות ניהול | תשואה נמוכה יותר ב־backtest היסטורי |

**מסקנה:**  
המחקר מראה ש**מיקוד ב־universe מוגדר** (20–50 מניות נזילות) עם **screening סדור** עדיף על בחירה אקראית. סקטורים שמובילים מתחלפים — 2024–2025: טק, בריאות; 2026: אנרגיה, תעשייה, utilities — ולכן **sector rotation** יכול להיות תוספת טובה לאסטרטגיה הקיימת.

---

## 2. איך סטארטפים וקרנות עושים את זה?

### מבנה Universe

| סוג | Universe | מסננים | מספר מניות סופי |
|-----|----------|--------|------------------|
| **קרן גדולה** | 25,000+ ניירות | נזילות, fundamentals, quality | 40–80 |
| **קרן קטנה / סטארטאפ** | 3,000–8,000 | נזילות ($50k+ vol), מחיר > $5 | 20–50 |
| **Retail Quant** | S&P 500 / Russell 3000 | Dollar volume top 10%, מחיר > $10 | 50–100 |

### מסנני נזילות נפוצים

- **Dollar volume 20d** ≥ $2M–$50M (אתה כבר משתמש ב־$2M)
- **מחיר** > $5–$10
- **נפח יומי** מספיק לביצוע ללא slippage משמעותי

### דוגמאות שיטות

1. **The Alpha Engineer / HCP Quant:**  
   ~15,000 מניות → כ־3,700 עוברים quality → כ־2,500 נזילות → Top 5% מדורגים ≈ 50 מניות.  
   עדכון שבועי.

2. **Julex Capital:**  
   תיק ממוקד 20–40 מניות. שילוב valuation, quality, momentum.

3. **Sector Rotation (Gary Antonacci):**  
   דירוג 9–11 sector ETFs לפי momentum (6–12 חודשים), החזקת Top 3–4, rebalance חודשי.

4. **Dual Momentum:**  
   Relative momentum (בין נכסים) + Absolute momentum (מול מזומן).  
   מקטין drawdown בתקופות bear.

---

## 3. האם גם אתה יכול לעשות את זה?

### כן — בהתאם למשאבים

| רכיב | מצב ב-SignalFlow | מה חסר |
|------|------------------|---------|
| Data Pipeline | Yahoo, SP/VIX | תמיכה ב-multi-symbol batch |
| Liquidity Gate | $2M dollar volume | כבר קיים |
| Backtest | תומך `--symbols` | מוכן |
| Paper Trading | symbol בודד | הרחבה ל־multi-symbol |
| Universe config | `symbols.yaml` (4 נכסים) | הרחבה לרשימה/חוקים |

אתה כבר קרוב — חסר בעיקר:
- הרחבת `symbols.yaml` ל־20–50 נכסים (או סקריפט screening)
- הרצת Paper/Backtest על רשימת symbols
- (אופציונלי) שכבת sector rotation על גבי best_combo

---

## 4. חמש אסטרטגיות מובילות לשלב

### אסטרטגיה 1: הרחבת Universe (Multi-Stock Screening)

**מה:** הרצת best_combo על 20–50 מניות נזילות במקום AAPL בלבד.

**איך:**  
- בחירת universe: S&P 500 top by dollar volume, או sectors מועדפים (XLK, XLV, XLF, וכו')  
- הרצת backtest לכל symbol  
- אופציה: שילוב weights לפי rank (למשל Sharpe או risk-adjusted return)

**מורכבות:** בינונית.  
**התאמה למערכת:** יש `run_strategy_compare --symbols`. צריך הרחבה קלה ל־Paper.

---

### אסטרטגיה 2: Sector Rotation (Top Sectors by Momentum)

**מה:** דירוג sector ETFs לפי momentum 6–12 חודשים, החזקת Top 3–4, rebalance חודשי.

**ETFs לדוגמה:**  
XLK (Tech), XLV (Health), XLF (Finance), XLE (Energy), XLI (Industrials), XLY (Consumer Disc.), XLP (Staples), XLU (Utilities), XLB (Materials).

**לוגיקה:**  
1. חישוב momentum = (price_now / price_6m_ago) - 1  
2. דירוג לפי momentum  
3. בחירת Top 3–4  
4. השקעה שווה או לפי momentum

**מורכבות:** בינונית.  
**התאמה למערכת:** שכבת on-top — מקבלת best_combo signals ואז מסננת לפי sector score. או אסטרטגיה נפרדת לגמרי.

**מחקר:** Moskowitz & Grinblatt (1999) — industry momentum חזק. Sector momentum CAGR 4–5% vs 6% equal-weight, אבל עם פחות סיכון ריכוזי.

---

### אסטרטגיה 3: Dual Momentum (Relative + Absolute)

**מה:** שילוב Relative momentum (דירוג נכסים) + Absolute momentum (סף מול T-Bills/cash).

**לוגיקה:**  
- Relative: דירוג נכסים לפי תשואה 12 חודשים  
- Absolute: אם הנכס הטוב ביותר לא עובר את T-Bills — מעבר ל־cash  
- מקטין חשיפה ב־bear markets

**מורכבות:** בינונית.  
**התאמה למערכת:** שכבת overlay על best_combo — אם absolute momentum שלילי, להוריד/לבטל long.

**מחקר:** Gary Antonacci — צמצום drawdown משמעותי.

---

### אסטרטגיה 4: Low-Volatility Tilt

**מה:** העדפת מניות/ETFs עם תנודתיות נמוכה יחסית.

**לוגיקה:**  
- חישוב תנודתיות 60/90 ימים  
- דירוג מהנמוך לגבוה  
- בחירת Bottom 20–30% (low vol) או שילוב vol כגורם שלילי ב־scoring

**מורכבות:** נמוכה.  
**התאמה למערכת:** יש לך Vol Target — אפשר להוסיף vol filter ל־universe: רק נכסים עם vol < X.

**מחקר:** Low-vol stocks נוטים להשיג תשואה עודפת על השוק בטווח ארוך (Low-Vol anomaly).

---

### אסטרטגיה 5: Short-Term Reversal (Mean Reversion)

**מה:** קניית מניות שירדו ב־1–4 שבועות (oversold) — ניצול mean reversion קצר טווח.

**לוגיקה:**  
- momentum_1m = (price_now / price_1m_ago) - 1  
- בחירת מניות עם momentum_1m הכי שלילי (מניות שירדו)  
- מותאם לאסטרטגיה mean-reverting

**מורכבות:** בינונית.  
**התאמה למערכת:** אתה כבר עובד עם regime mean_reverting. אפשר להוסיף screening: נכנס רק לנכסים ב־oversold (1m return שלילי) כשהר regime הוא mean_reverting.

---

## 5. טבלת השוואה — מורכבות והתאמה ל-SignalFlow

| # | אסטרטגיה | מורכבות | התאמה | השפעה צפויה |
|---|----------|----------|-------|---------------|
| 1 | Multi-Stock Universe | בינונית | גבוהה — כבר יש תשתית | גיוון, הפחתת ריכוז |
| 2 | Sector Rotation | בינונית | בינונית — שכבת on-top | ניצול תזוזות סקטוריאליות |
| 3 | Dual Momentum | בינונית | גבוהה — overlay על best_combo | צמצום drawdown |
| 4 | Low-Volatility Tilt | נמוכה | גבוהה — Vol Target קיים | הפחתת תנודתיות |
| 5 | Short-Term Reversal | בינונית | גבוהה — regime mean_rev קיים | חיזוק mean-reversion |

---

## 6. סדר יישום מומלץ

1. **הרחבת Universe (אסטרטגיה 1)** — הרצת best_combo על 20–30 מניות. הכי קרוב למה שיש.  
2. **Low-Volatility Tilt (אסטרטגיה 4)** — הוספת vol filter או vol scoring. שינוי קטן.  
3. **Dual Momentum overlay (אסטרטגיה 3)** — השלמת best_combo עם absolute momentum.  
4. **Short-Term Reversal screening (אסטרטגיה 5)** — שילוב עם regime mean_reverting.  
5. **Sector Rotation (אסטרטגיה 2)** — שכבת sector ETFs נפרדת.

---

## 7. מקורות והפניות

- Morgan Stanley 2024 Midyear Outlook — Hedge Funds  
- QuantConnect — Universe Selection, Liquidity Effect  
- Gary Antonacci — Dual Momentum (2012)  
- Moskowitz & Grinblatt — Industry Momentum (1999)  
- The Alpha Engineer / HCP Quant — Microcap & concentrated quant  
- Julex Capital — Concentrated Multi-Factor  
- QuantPedia — Sector Momentum improvements  

---

*נוצר: 2026-03 — תחקיר ארכיטקטורה ואסטרטגיות*
