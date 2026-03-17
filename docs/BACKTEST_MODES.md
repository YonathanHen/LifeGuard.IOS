# Backtest Modes — דגלים ותיעוד

כל מצב (mode) מוגדר ב־`config/backtest_modes.json` וניתן להפעלה עם:
```bash
python scripts/run_backtest.py --mode <שם_המצב>
```

ברירת המחדל: **stat_only** — המצב הרווחי שהוכח.

---

## טבלת המצבים

| Mode | use_ml | ml_threshold | ml_negative_filter | commission | slippage | תוצאות נצפות |
|------|--------|--------------|--------------------|------------|----------|--------------|
| **stat_only** | false | - | - | 5 bps | 3 bps | Return ~21-24%, Sharpe ~1.0, MaxDD -10.7%, ~185 trades |
| stat_only_no_costs | false | - | - | 0 | 0 | Gross baseline |
| ml_threshold_050 | true | 0.5 | false | 5 | 3 | 115 trades, 22.1%, avg 0.192% Safe |
| ml_threshold_060 | true | 0.6 | false | 5 | 3 | 0 trades |
| ml_threshold_070 | true | 0.7 | false | 5 | 3 | 0 trades |
| ml_threshold_085 | true | 0.85 | false | 5 | 3 | ~0 trades (לא נבדק) |
| ml_threshold_090 | true | 0.9 | false | 5 | 3 | 5 trades, -3.2% |
| ml_negative_filter | true | - | true (0.8) | 5 | 3 | חוסם רק P_down>0.8 |
| **best_combo** | false | - | - | 5 | 3 | MR x2 + ATR + Vol: Sharpe 1.99, Return 63%, DD -7.6% |

---

## פרמטרים מלאים לפי דגל

### use_ml (bool)
- **false** — Stat Core בלבד (ARIMA+GARCH+Regime+Cross-asset). ברירת המחדל הרווחית.
- **true** — דורש גם אישור LSTM (P_up >= ml_threshold).

### ml_threshold (float)
- רק כאשר use_ml=true. סף P_up מינימלי לכניסה.
- 0.5 = כמעט כל הטריידים (דומה ל-Stat)
- 0.6+ = המודל הנוכחי חוסם הכל (0 trades)

### ml_negative_filter (bool)
- **false** — פילטר חיובי: נכנס רק כש-P_up >= threshold
- **true** — פילטר שלילי: נכנס אלא אם P_down > disaster_threshold (ברירת מחדל 0.8)

### commission_bps, slippage_bps
- עמלות round-trip. 5+3 = 16 bps = 0.16% לכל כניסה.

---

## דוגמאות הרצה

```bash
# המצב הבסיסי הרווחי (ברירת מחדל)
python scripts/run_backtest.py

# במפורש
python scripts/run_backtest.py --mode stat_only

# נסיון ML — כבה בקלות אם לא עובד
python scripts/run_backtest.py --mode ml_threshold_050

# Override פרמטרים
python scripts/run_backtest.py --mode stat_only --symbol MSFT --period 2y

# השילוב המומלץ (MR x2 + ATR Stop + Vol Target)
python scripts/run_backtest.py --mode best_combo --period 3y --end-date 2026-03-02
```

---

## רשימת מצבים

```bash
python scripts/run_backtest.py --list-modes
```

## Minimum Gain Filter — תוצאות בפועל

מריץ: `python scripts/min_gain_filter.py --thresholds 0.5,0.6,0.7,0.8,0.85`

**תוצאות מהרצה (AAPL, 2y):**

| P_up ≥ | Trades | Return | Avg/Trade | Safe? |
|--------|--------|--------|-----------|-------|
| 0.50 | 115 | 22.1% | 0.192% | ✓ |
| 0.60 | 0 | - | - | - |
| 0.85 | 0 | - | - | - |

ב־0.50: avg 0.192% > עלות 0.16% → Safe. ב־0.6+ המודל חוסם הכל.

---

## חזרה למצב קודם

אם שינית קוד או פרמטרים והכל "התקלקל" — הרץ:
```bash
python scripts/run_backtest.py --mode stat_only
```
זה מחזיר למצב שהוכח: Stat-only, 5+3 bps, 3y AAPL.
