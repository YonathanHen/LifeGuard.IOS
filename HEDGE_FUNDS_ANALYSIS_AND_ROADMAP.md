# SignalFlow — ניתוח קרנות הגידור והדרך קדימה

*מה עושים השועלים הגדולים • מה יש לנו • איך להשתפר*

---

## עיקרון מרכזי — לא "mini-Medallion"

**ההצלחה לא מגיעה מלהיות "כמו הקרנות"** — אלא מלהיות **הרבה יותר ממושמעת**, בקנה מידה קטן.

**מסגור:** Build a small, disciplined, **single-edge shop** — Edge אחד (Stat Core), פילטרים חכמים (Regime, Rules, ML), גיוון נכסים רק כדי להקטין סיכון. לא: 8 אסטרטגיות, 5 שכבות ML, 20 מקורות דאטה.

*ראה גם: `GO_NO_GO_FRAMEWORK.md` — מתי עוצרים פיתוח ועוברים למסחר.*

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

**סדר עדיפות (חובה):**

| # | משימה | תיאור | הערה |
|---|--------|-------|------|
| 1 | **Paper Trading** | Gate אמיתי — רישום החלטות, PnL, מדדי אמון | **חובה ראשון** |
| 2 | **Multi-symbol** | אותו קוד על SPY, QQQ, MSFT — **בלי tuning לנכס** | Robustness בלבד |
| 3 | **Factor layer** | Momentum (12-1) בלבד — Value ל-daily חלש | |
| 4 | **Threshold Plateau** | Grid search על Stat Core thresholds | |

⚠️ Multi-symbol: **אותו סט חוקים, אותה לוגיקה** — לא לכייל thresholds לכל מניה.

### Phase 2 — Deepening (3–6 חודשים)

| # | משימה | תיאור | מאמץ |
|---|--------|-------|------|
| 5 | **Weak predictors** | **חוקים חלשים** — לא מודלים קטנים. Veto/confirmation: volatility spike → veto, volume anomaly → reduce confidence, regime mismatch → block | גבוה |
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
- ❌ אלפי weak predictors — לא ריאלי ולא נחוץ
- ❌ Alternative data לפני scale — מעשית לא ריאלי
- ❌ "עוד קצת ML = Medallion" — הקרנות מצליחות מגיוון, נפח, משמעת — לא מ-ML לבד

---

## סיכום — הדרך להצלחה

1. **התבסס על Stat Core** — כבר מייצר Alpha; לשפר איטרציבית.
2. **הוסף Factors** — Momentum ו-Value הם מוכחים; שילוב פשוט יחסית.
3. **גוון נכסים** — SPY, QQQ, כמה מניות ליבה; פחות תלות ב-AAPL.
4. **Paper Trading** — 3–6 חודשים לפני כסף אמיתי.
5. **Ensemble של weak predictors** — כיוון ל-Medallion, ברמת מורכבות שמתאימה.

---

*מסמך ייחוס — 2026-03. מקורות: Hedgeweek, Business Insider, QuantStrategy, AQR, JPM quant research.*
