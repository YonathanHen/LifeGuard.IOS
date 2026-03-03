# SignalFlow — בדיקה מקיפה על זמן ארוך

*נוצר: 2026-03-03*

---

## 1. Paper Trading Decisions — 6 חודשים

**תקופה:** 29.08.2025 — 02.03.2026  
**מספר ימי מסחר:** 126  
**סמל:** AAPL

| מדד | ערך |
|-----|-----|
| **Decision Consistency** | 60.8% |
| **Exposure** | 46.0% |
| **Avg Holding Period** | 2.3 ימים |
| **ימי Long** | 58 מתוך 126 |

**משמעות:**
- המערכת הייתה Long ב־46% מהימים
- Consistency מעל 60% — שינויי החלטה מתונים
- ממוצע החזקה ~2.3 ימים — סגנון קצר־טווח

---

## 2. Backtest — 2 שנים (היסטורי)

**תקופה:** 2 שנים | עלויות: 5+3 bps

| מדד | Stat Only | Stat + ML |
|-----|-----------|-----------|
| **Sharpe Ratio** | 0.597 | **0.848** |
| **Max Drawdown** | -18.2% | -18.2% |
| **Total Return** | 8.0% | **11.8%** |
| **N Trades** | 130 | 125 |
| **Hit Rate** | 51.5% | 51.2% |
| **Exposure** | 58.3% | 56.1% |

**לפי Regime (Stat+ML):**
- trend: Sharpe 0.69
- mean_reverting: Sharpe **1.01**
- high_volatility: אין טריידים

**Decision Density:**
- Stat: 65 trades/yr | 1.0 avg days | 0.06% avg ret/trade
- Stat+ML: 62.5 trades/yr | 1.0 avg days | **0.09% avg ret/trade**

---

## 3. סיכום והמלצות

### מה עובד
1. **שיפור מובהק מ־ML** — Sharpe עולה מ־0.60 ל־0.85, תשואה מ־8% ל־11.8%
2. **משך תקופה רלוונטי** — 6 חודשים של החלטות, 2 שנים של backtest
3. **Exposure סביר** — 46% מ־paper תואם ל־~56% מ־backtest

### מגבלות
1. **Blocked Loss Rate / Net EV** — חישוב מלא דורש backtest עם `--stability` (Error Type Analysis). הרצה ארוכה, ונפגעה מ־FRED rate limit.
2. **תקופת Paper** — 6 חודשים מתחת ל־מינימום 3 חודשים ל־Gate 3; מומלץ להמשיך ל־3 חודשים לפחות.
3. **FRED API** — הגבלת קצב; מומלץ להמתין ולהריץ Error Type Analysis מאוחר יותר.

### הרצות מומלצות להמשך

```bash
# Backtest 5y עם Error Type Analysis (אחרי reset FRED)
python scripts/run_backtest_with_ml.py --period 5y --stability

# הרצה יומית
python scripts/paper_trading_daily.py

# Batch להוספת תקופה היסטורית
python scripts/paper_trading_daily.py --batch-start 2024-01-01 --batch-end 2025-08-28

# דוח Gate 2
python scripts/paper_trading_report.py --start 2025-09-01 --end 2026-03-02 --period 5y
```

---

*גרסה 1.0 — 2026-03-03*
