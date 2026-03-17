# SignalFlow — מחקר אסטרטגיות ומסקנות

*מסמך מקיף: כל האסטרטגיות הקיימות | מחקר גלובלי | 5 ההמלצות המובילות*

---

## חלק א' — כל האסטרטגיות הקיימות בתוכנה

### 1. Stat Core (ARIMA + GARCH)

| פרמטר | ערך | תיאור |
|-------|-----|--------|
| **ARIMA** | order (2,0,2) daily | חיזוי כיוון (up/down/flat) + magnitude (low/medium) |
| **GARCH** | risk_timing daily | תזמון תנודתיות, volatility_bucket (low/med/high) |
| **has_statistical_edge** | direction≠flat + magnitude≥low | תנאי AND — חוסם כשכיוון לא ברור |

**תוצאות:**
- ✅ **הכי מוצלח:** Stat Only 3y — Sharpe 1.76, Return 52.9%, 154 trades
- ✅ 2y: Sharpe 1.33, Return 15–22%
- ⚠️ 5y: Return 4–10% — תקופה קשה (קורונה, התאוששות)

---

### 2. Rule Engine (שערי סינון)

| שער | תנאי | סטטוס |
|-----|------|--------|
| **Liquidity** | dollar_volume_20d ≥ $2M | פעיל — חוסם נכסים לא נזילים |
| **Cross-Asset** | SP↑+VIX↑ → block | פעיל — חוסם כש-SP500 עולה ו-VIX קופץ (קונפליקט) |
| **Regime Stable** | regime ≠ high_volatility | פעיל — חוסם ב-high_vol |
| **Forced Cooldown** | 3 ימים אחרי regime shift | פעיל — ב-API/validation |
| **Data Stable** | z-score לא outlier | פעיל |

**הערה:** Cross-Asset ו-Liquidity מראים **רלוונטיות** — מניעת טריידים במצבי סיכון.

---

### 3. Regime Detection (HMM)

| Regime | Sizing כיום | תוצאות לפי regime |
|--------|-------------|-------------------|
| **trend** | 50% position (pos_mult=0.5) | Sharpe 2.52, DD -6.5%, 55 trades |
| **mean_reverting** | 100% | Sharpe 2.14, DD -6.0%, 99 trades |
| **high_volatility** | 0% (חוסם לגמרי) | אין טריידים |

**הערה:** הקטנת גודל ב-trend מבוססת על ניתוח Gemini — Sharpe ב-trend חלש יותר.

---

### 4. ML Layer (LSTM)

| מצב | תיאור | תוצאות |
|-----|--------|---------|
| **Stat Only** | use_ml=False | ✅ Sharpe 1.76, Return 52.9% |
| **Negative Filter** (P_down>0.8) | חוסם רק אסונות | △ 5y: Sharpe 0.17–0.24, Return 4–10% |
| **Legacy AND** (P_up≥0.6) | חייב אישור ML | ✅ Sharpe 2.12, DD -3.6%, 70 trades — פחות טריידים, DD נמוך |
| **ml_threshold_050** | P_up≥0.5 | 115 trades, 22.1%, avg 0.192% — Safe vs cost |

**מסקנה:** LSTM עם **bias פסימי** — Legacy AND חוסם כמעט הכל. Negative Filter מאזן טוב יותר ב-5y.

---

### 5. Position Sizing (Regime)

| Regime | מכפיל נוכחי | מכפיל מומלץ (LEVERAGE) |
|--------|-------------|------------------------|
| trend | 0.5 | 0.5 (קיים) |
| mean_reverting | 1.0 | **2.0** (MR x2 — לא מיושם!) |
| high_vol | 0 | 0 |

**פער:** MR x2 מתועד ב-LEVERAGE_ANALYSIS (52.1% vs 26.4% ב-5y) — **לא קיים ב-engine**.

---

### 6. אסטרטגיות נוספות (סקריפטים נפרדים)

| אסטרטגיה | סקריפט | תוצאות | סטטוס |
|----------|--------|--------|--------|
| **Min Gain Filter** | min_gain_filter.py | P_up≥0.5: 115 trades, 22.1%, avg 0.192% | לא משולב |
| **ML Threshold Stability** | ml_threshold_stability.py | Grid 0.52–0.70, חיפוש Plateau | כלי אימות |
| **Slippage Sensitivity** | slippage_sensitivity.py | בדיקת avg_trade vs 0.5% | כלי אימות |
| **Leverage Simulation** | leverage_simulation.py | MR x2 → 52.1% | סימולציה נפרדת |

---

### סיכום חלק א' — מה עובד ומה לא

| אסטרטגיה | עובד | לא עובד | הערות |
|----------|------|---------|--------|
| Stat Core | ✅ | — | הבסיס החזק |
| Regime 50% Trend | ✅ | — | מקטין סיכון ב-trend |
| Cross-Asset | ✅ | — | חוסם קונפליקטים |
| Liquidity Gate | ✅ | — | סינון בסיסי |
| Stat Only 3y | ✅ | — | הכי מוצלח |
| Stat+ML Negative 5y | △ | Return נמוך | תקופה קשה |
| Legacy AND | ✅ | חוסם הכל ב-daily | טוב ל-weekly |
| MR x2 | — | לא מיושם | פוטנציאל +25% |
| Min Gain Filter | △ | לא משולב | 22.1% Safe |

---

## חלק ב' — מחקר: מה עושות חברות וסטארטאפים

### 2.1 קרנות הגידור המובילות

| קרן | תשואה שנתית | אסטרטגיה |
|-----|-------------|-----------|
| **Renaissance Medallion** | ~30% | אלפי weak predictors, HFT |
| **Bridgewater Pure Alpha** | 12%+ | Rules-based, regime-adaptive |
| **Point72** | 15% | AI ב-60% מההחלטות, alternative data |
| **Two Sigma** | 11–14% | ML, alternative data |
| **D.E. Shaw** | 18–36% | Multi-strategy, stat arb |

### 2.2 עקרונות משותפים

1. **Regime Switching** — HMM/state models כמו שלנו, דינמיקה לפי מצב שוק
2. **Factor Investing** — Momentum, Value, Volatility (AQR, JPM)
3. **Ensemble של weak predictors** — לא מודל אחד חזק, הרבה חלשים
4. **Alternative Data** — sentiment, order flow, credit spread (כבר יש לנו)
5. **Volatility Scaling** — התאמת גודל פוזיציה לתנודתיות
6. **Kelly Criterion** — מינוף אופטימלי (בפועל: fractional 0.25–0.5)

### 2.3 סטארטאפים ו-Academia

| מקור | אסטרטגיה | תוצאות |
|------|-----------|--------|
| **AI NeuroSignal** | 20 agents, dynamic rotation | +90.6% return, 73% false signal reduction |
| **Increase Alpha** | Deep learning | Sharpe >2.5, DD ~3% |
| **Agentic trading** | Multi-agent orchestration | 20.42% return, Sharpe 2.63 |
| **Regime-Switching Factors** | HMM + Black-Litterman | IR 0.05→0.4 |
| **Volatility Targeting** | target_vol/realized_vol | תקציב סיכון קבוע |
| **ATR Trailing Stops** | ATR×2–3 מתחת למחיר | הגנה על רווחים |

### 2.4 מה אנחנו כבר עושים (התאמה)

| עקרון חיצוני | SignalFlow | חסר? |
|--------------|------------|------|
| Regime detection | HMM 3 states | ✔ |
| Alternative data | VIX, credit spread, yield curve | ✔ |
| Cross-asset | SP/VIX alignment | ✔ |
| Position sizing | Regime-based (50% trend) | △ MR x2 חסר |
| Volatility scaling | — | ❌ |
| Kelly / fractional sizing | — | ❌ |
| ATR trailing stop | — | ❌ |
| Multi-asset | AAPL בלבד | ❌ |
| Factor layer (momentum) | — | ❌ |

---

## חלק ג' — 5 ההמלצות המובילות

### המלצה 1: **MR x2 — מכפיל Mean Reverting**

**מה:** ב-regime mean_reverting, להכפיל את גודל הפוזיציה (מ-1.0 ל-2.0).

**למה:** סימולציה מראה 26.4% → 52.1% ב-5y. Max DD עולה מ-13% ל-22%.

**יישום:** דגל `--mean-rev-mult` ב-run_backtest.py, פרמטר `mean_rev_position_mult` ב-BacktestEngine.

**קוד:**
```python
# engine: pos_mult = 0.5 if regime=="trend" else (mean_rev_mult if regime=="mean_reverting" else 0)
# mean_rev_mult: 1.0 (default), 1.5, 2.0
```

---

### המלצה 2: **Volatility Targeting — התאמת גודל לתנודתיות**

**מה:** Scale position לפי `target_vol / realized_vol`. כשהתנודתיות גבוהה — להקטין.

**למה:** קרנות כמו Bridgewater משתמשות. שמירה על תקציב סיכון קבוע.

**יישום:** דגל `--vol-target` + `target_vol_ann=0.15`. חישוב rolling 20d vol, כפל פוזיציה ב-min(1, target/realized).

**קוד:**
```python
# position *= min(1.0, target_vol_ann / (rolling_vol_20d + 1e-8))
# Clamp 0.25–1.5 למניעת קיצון
```

---

### המלצה 3: **ATR Trailing Stop — יציאה דינמית**

**מה:** במקום "מחזיק עד יום מחר" — יציאה אם המחיר ירד מתחת ל-Entry - ATR×2.

**למה:** הגנה על רווחים, הפחתת drawdown. מקובל ב-quant (StrategyQuant, QuantStrategy).

**יישום:** דגל `--atr-stop` (0=off, 2=default). ATR(14), multiplier 2–3.

**הערה:** דורש שינוי לוגיקת backtest — מעקב אחרי intraday/high-low. אם אין — ניתן ליישם כ-"אם return יומי <-2×ATR → יציאה".

---

### המלצה 4: **Fractional Kelly — גודל לפי ביטחון**

**מה:** גודל פוזיציה לפי Kelly: `f = 2p - 1` (p=hit_rate). fractional 0.5 Kelly.

**למה:** מיקסום צמיחה ארוכת טווח. Buffett, Gross משתמשים. מחקרים: 70–80% מהתשואה מגיעה מ-position sizing.

**יישום:** דגל `--kelly-frac` (0=off, 0.5=half Kelly). שימוש ב-hit_rate היסטורי או rolling.

**קוד:**
```python
# kelly_f = 2 * hit_rate - 1  # symmetric payoff
# position *= max(0.25, min(1.0, kelly_f * kelly_frac))
```

---

### המלצה 5: **Multi-Symbol — גיוון נכסים**

**מה:** הרצת אותו Stat Core על SPY, QQQ, MSFT בנוסף ל-AAPL. **בלי** כיוונון שונה — אותם thresholds.

**למה:** Renaissance, Two Sigma — גיוון מפחית סיכון. AAPL יחיד = tail risk.

**יישום:** דגל `--symbols AAPL,SPY,QQQ` — backtest נפרד לכל נכס, או פורטפוליו מאוחד (ממוצע/סכום לפי weight).

**הערה:** ה-HEDGE_FUNDS כבר ממליץ — "אותו סט חוקים, אותה לוגיקה".

---

## תוצאות אימות (2026-03-17, 3y end 2026-03-02)

### בודדות
| אסטרטגיה | Sharpe | Return | Max DD | Trades |
|----------|--------|--------|--------|--------|
| baseline | 1.64 | 36.5% | -8.5% | 154 |
| MR x2 | 1.55 | 68.4% | -13.8% | 154 |
| vol_target | 1.66 | 27.2% | -6.3% | 154 |
| ATR Stop x2 | 1.83 | 40.1% | -7.0% | 154 |
| kelly | 1.40 | 17.8% | -5.0% | 154 |
| MR x2 + Vol | 1.68 | 54.6% | -9.6% | 154 |

### שילובים (Combinations)
| שילוב | Sharpe | Return | Max DD |
|-------|--------|--------|--------|
| **MR x2 + ATR Stop + Vol Target** | **1.986** | 62.9% | -7.6% |
| MR x2 + ATR Stop | 1.744 | **77.2%** | -11.1% |
| ATR Stop + Vol Target | 1.940 | 30.7% | **-5.2%** |

**מסקנות:** השילוב השלישי (MR x2 + ATR + Vol) הוא הטוב ביותר — Sharpe 1.99, Return 63%, DD סביר. MR x2 + ATR מניב Return הכי גבוה (77%). `docs/STRATEGY_COMPARE_RESULTS.md` מעודכן.

---

## חלק ד' — סיכום מעשי

### דגלים להפעלה מיידית (בקוד)

| דגל | קובץ | מאמץ | פוטנציאל |
|-----|------|-------|----------|
| `--mean-rev-mult 2.0` | engine.py, run_backtest.py | נמוך | +25% return (לפי סימולציה) |
| `--vol-target 0.15` | engine.py | בינוני | הפחתת DD, תקציב סיכון |
| `--kelly-frac 0.5` | engine.py | נמוך | שיפור risk-adjusted |
| `--symbols AAPL,SPY` | run_backtest.py (loop) | נמוך | robustness |
| `--atr-stop 2` | engine.py | בינוני | הגנה על רווחים |

### שילוב מומלץ (אומת 2026-03-17)

```bash
python scripts/run_backtest.py --mode stat_only --period 3y \
  --mean-rev-mult 2.0 --atr-stop 2 --vol-target 0.15
```

תוצאות: Sharpe 1.99, Return 62.9%, Max DD -7.6%.

### סדר עדיפות

1. **MR x2** — כבר מחקרי, סימולציה מוכחת. **להפעיל ראשון.**
2. **Multi-Symbol** — פשוט, robustness. **להפעיל שני.**
3. **Volatility Targeting** — תקציב סיכון קבוע.
4. **Kelly fractional** — שיפור sizing.
5. **ATR Stop** — דורש יותר לוגיקה (high/low).

---

## מקורות

- Bridgewater Pure Alpha, Point72 strategy teardowns
- Princeton: Factor Momentum and Regime-Switching
- Kelly Criterion: PyQuant News, QuantStrategy.io
- Volatility Targeting: BackQuant, Quant Stack Exchange
- ATR Stops: StrategyQuant, QuantStrategy
- storage/LEVERAGE_ANALYSIS_AND_RECOMMENDATIONS.md
- storage/SUCCESS_HISTORY_AND_REVERT_ANALYSIS.md
- HEDGE_FUNDS_ANALYSIS_AND_ROADMAP.md
- ALGORITHM_SPEC.md

---

*נוצר: 2026-03 — מחקר מקיף. להפעלת המלצות: עדכון engine + run_backtest עם הדגלים.*
