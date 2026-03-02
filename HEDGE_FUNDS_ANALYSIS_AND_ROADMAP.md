# SignalFlow — ניתוח קרנות הגידור והדרך קדימה

*מה עושים השועלים הגדולים • מה יש לנו • איך להשתפר*

---

## חלק א' — מה עושים המצליחים

### 1.1 הביצועים (2024)

| קרן | תשואה / רווח | אסטרטגיה מרכזית |
|-----|-------------|------------------|
| **Renaissance Medallion** | ~30% לשנה | Quant, אלפי מודלים חלשים, HFT/MF |
| **Renaissance Institutional** | 15–23% | Stat arb, pattern recognition |
| **D.E. Shaw** | 18% (Composite), 36% (Oculus) | Multi-strategy, stat arb |
| **Citadel** | 15–22% | Multi-strategy, quant + discretionary |
| **Two Sigma** | 11–14% | ML, alternative data |
| **Millennium** | 15%, $74B AUM | Multi-strategy |

רוב הקרנות הוציאה double-digit, אבל פחות מ-S&P 500 (23%) — המודלים שלהם ממוקדים ב-**תשואה מתואמת-סיכון**, לא רק ב-beat השוק.

---

### 1.2 עקרונות אסטרטגיים

| עקרון | Renaissance | D.E. Shaw / Two Sigma | SignalFlow כיום |
|-------|-------------|------------------------|-----------------|
| **נתונים** | Petabytes, מאות שנים, data ייחודי | Alternative data, sentiment, order flow | Yahoo, FRED, VIX — מוגבל |
| **מודלים** | אלפי predictors חלשים, ensemble | ML, stat arb, factors | LSTM יחיד, ARIMA+GARCH |
| **תדירות** | דקות–שעות (HFT/MF) | מגוון | יומי |
| **גיוון** | מאות/אלפי נכסים | Multi-asset | AAPL (בעיקר) |
| **מיקרו-מבנה** | Order book, latency | Smart execution | — |
| **צוות** | מתמטיקאים, פיזיקאים | Quant + engineering | — |

---

### 1.3 האסטרטגיות הנפוצות

1. **Statistical Arbitrage** — ניצול סטיות זמניות בין נכסים מתאמים (pairs, cross-asset).
2. **Ensemble של predictors חלשים** — מאות/אלפי מודלים קטנים (50.1% דיוק), אוגרים ל-edge יציב.
3. **Factor investing** — Momentum, Value, Carry, Volatility; מחקר AQR/JPM.
4. **Alternative data** — סנטימנט, לווינים, filings, order flow.
5. **Execution optimization** — ML ל-minimize impact ולשפר מימוש רווחים.
6. **Regime detection** — HMM / state models (כמו שלנו) לזיהוי שינויי מצב שוק.

---

## חלק ב' — איפה אנחנו עומדים

### 2.1 מה עובד אצלנו

| רכיב | סטטוס | הערות |
|------|--------|-------|
| Stat Core (ARIMA+GARCH) | ✔ | Sharpe ~1.76, DD -11.3% |
| Regime (HMM) | ✔ | trend / mean_reverting / high_vol |
| Rule Engine | ✔ | Liquidity, cross-asset |
| LSTM | △ | Stat Core חזק ממנו כיום |
| Point-in-time | ✔ | Validation ללא look-ahead |
| Backtest + costs | ✔ | 5+3 bps |

### 2.2 מה חסר (יחסית לשועלים)

| פער | רמת מאמץ | פוטנציאל |
|-----|-----------|----------|
| גיוון נכסים | בינוני | הפחתת סיכון, robustness |
| Ensemble predictors חלשים | גבוה | Edge יציב יותר |
| Alternative data | גבוה | Alpha נוסף |
| Multi-timeframe | נמוך | שיפור דיוק |
| Factor layer (Momentum/Value) | בינוני | Alpha מוכח במחקר |
| Execution optimization | גבוה | שיפור רווח נטו |

---

## חלק ג' — תוכנית שיפור מעשית

### Phase 1 — Quick Wins (1–3 חודשים)

| # | משימה | תיאור | מאמץ |
|---|--------|-------|------|
| 1 | **Multi-symbol** | הרצת אותה לוגיקה על SPY, QQQ, MSFT — בדיקת robustness | נמוך |
| 2 | **Factor layer** | Momentum (12-1), Value (P/B) — סינון/דירוג לפני Stat Core | בינוני |
| 3 | **Threshold optimization** | Grid search על ARIMA/GARCH thresholds — מיקום Plateau | נמוך |
| 4 | **Paper Trading** | רישום החלטות ו-PnL — אימות בזמן אמת | בינוני |

### Phase 2 — Deepening (3–6 חודשים)

| # | משימה | תיאור | מאמץ |
|---|--------|-------|------|
| 5 | **Weak predictors** | מודלים קטנים (volatility regime, volume spike, sentiment) — ensemble | גבוה |
| 6 | **Alternative data** | News sentiment (free APIs), options put/call — כפייה נוספת | גבוה |
| 7 | **Dual-Track ML** | Anchor (5–7y) + Scout (12–18mo) — מנגנון מגן מ-Alpha Decay | בינוני |
| 8 | **Pairs / Stat arb** | זיהוי זוגות מתאמים (AAPL-MSFT) — mean reversion | גבוה |

### Phase 3 — Scale (6–12 חודשים)

| # | משימה | תיאור |
|---|--------|-------|
| 9 | **Portfolio construction** | Kelly Criterion, risk parity — הקצאת הון אופטימלית |
| 10 | **Execution layer** | VWAP/TWAP, minimize slippage |
| 11 | **Infrastructure** | Real-time data, automation, monitoring |

---

## חלק ד' — מה לא לנסות (כרגע)

- ❌ HFT — דורש latency, infrastructure, עלויות ענק
- ❌ Petabytes of data — לא רלוונטי ל-retail/small quant
- ❌ 복잡ות יתר — עדיף few strategies שעובדות מאשר עשרות שלא מאומתות

---

## סיכום — הדרך להצלחה

1. **התבסס על Stat Core** — כבר מייצר Alpha; לשפר איטרציבית.
2. **הוסף Factors** — Momentum ו-Value הם מוכחים; שילוב פשוט יחסית.
3. **גוון נכסים** — SPY, QQQ, כמה מניות ליבה; פחות תלות ב-AAPL.
4. **Paper Trading** — 3–6 חודשים לפני כסף אמיתי.
5. **Ensemble של weak predictors** — כיוון ל-Medallion, ברמת מורכבות שמתאימה.

---

*מסמך ייחוס — 2026-03. מקורות: Hedgeweek, Business Insider, QuantStrategy, AQR, JPM quant research.*
