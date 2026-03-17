# SignalFlow — תוצאות 5y ו־Multi-Symbol

*אימות אסטרטגיות בתקופה ארוכה ונכסים מרובים*

---

## 1. Backtest 5 שנים (AAPL)

**תאריך הרצה:** 2026-03-17

| אסטרטגיה | Sharpe | Return | Max DD | Trades |
|----------|--------|--------|--------|--------|
| baseline (Stat Only) | 0.82 | 38.7% | -12.6% | 360 |
| MR x2 | 0.91 | 86.3% | -23.5% | 355 |
| MR x2 + ATR Stop | **1.27** | **143.1%** | -20.0% | 360 |
| MR x2 + ATR + Vol | 0.99 | 65.2% | -17.3% | 360 |

**מסקנות 5y:**
- MR x2 + ATR Stop מוביל ב־Return (143%) וב־Sharpe (1.27)
- MR x2 + ATR + Vol שמרני יותר (65%, DD -17.3%) — תקציב סיכון קבוע
- baseline 38.7% — סביר לתקופה כוללת קורונה

---

## 2. השוואה 3y vs 5y (AAPL)

| אסטרטגיה | 3y Sharpe | 3y Return | 5y Sharpe | 5y Return |
|----------|-----------|-----------|----------|-----------|
| baseline | 1.64 | 36.5% | 0.82 | 38.7% |
| MR x2 | 1.55 | 68.4% | 0.91 | 86.3% |
| best_combo (MR+ATR+Vol) | 1.99 | 62.9% | 0.99 | 65.2% |

5y מראה Sharpe נמוך יותר (תקופת קורונה קשה) אך Return דומה או גבוה יותר — הצטברות לאורך זמן.

---

## 3. Multi-Symbol (AAPL, SPY, QQQ)

**תאריך הרצה:** 2026-03-17 | period 3y, end 2026-03-02

| אסטרטגיה | Sharpe | Return | Max DD |
|----------|--------|--------|--------|
| baseline (ממוצע 3 נכסים) | — | 35.2% | -8.5% |
| mr_x2_atr_vol (ממוצע) | 1.26 | **24.8%** | -9.4% |

גיוון מפחית Return (24.8% vs 56.8% ב-AAPL בלבד) אך מפחית תלות בנכס יחיד.

**פקודה:**
```bash
python scripts/run_strategy_compare.py --period 3y --symbols AAPL,SPY,QQQ
```

---

## 4. המלצה מעשית

| תקופה | אסטרטגיה מומלצת | דגל |
|------|------------------|-----|
| 3y (חלון שורי) | best_combo | `--mode best_combo` |
| 5y (תקופה מלאה) | MR x2 + ATR | `--mean-rev-mult 2.0 --atr-stop 2` |

---

*מקור: storage/strategy_compare_results.json | run_strategy_compare.py*
