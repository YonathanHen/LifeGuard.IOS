# SignalFlow — אסטרטגיות מורחבות (Multi-Universe, Dual Momentum, Low-Vol, Reversal, Sector Rotation)

*מימוש: דגלים, סקריפטים, תיעוד — ניתן לבדיקה עצמית*

---

## 1. Multi-Stock Universe

### מה

הרצת best_combo על 25 נכסים נזילים (מרשימת `config/symbols.yaml`).

### דגלים

```bash
# Backtest על כל ה-universe
python scripts/run_multi_universe.py --period 3y --end-date 2026-03-02

# בדיקה מהירה — 5 נכסים בלבד
python scripts/run_multi_universe.py --period 3y --limit 5

# Strategy Compare עם רשימה מותאמת
python scripts/run_strategy_compare.py --symbols AAPL,MSFT,GOOGL,NVDA,META --period 3y
```

### תצורה

`config/symbols.yaml` → `universe: [AAPL, MSFT, ...]`

---

## 2. Low-Vol Tilt

### מה

הקטנת פוזיציה כשהתנודתיות (vol) נמצאת ברבעון העליון של 60 הימים.

### דגלים

```bash
# Backtest
python scripts/run_backtest.py --mode best_combo --low-vol-tilt --period 3y

# Paper
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --low-vol-tilt --dry-run
```

---

## 3. Dual Momentum (Absolute Momentum)

### מה

אם תשואת SP500 ב-12 חודשים < ~4% (risk-free) — מעבר ל-cash (אין long).

### דגלים

```bash
# Backtest
python scripts/run_backtest.py --mode best_combo --dual-momentum --period 3y

# Paper
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --dual-momentum
```

---

## 4. Short-Term Reversal

### מה

ב-regime mean_reverting: נכנסים רק כשה־stock oversold (תשואה 1 חודש < 0).

### דגלים

```bash
# Backtest
python scripts/run_backtest.py --mode best_combo --short-term-reversal --period 3y

# Paper
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --short-term-reversal
```

---

## 5. Sector Rotation

### מה

דירוג 9 sector ETFs לפי momentum 6 חודשים. החזקת Top 3.

### דגלים

```bash
# ריצה יומית / שבועית — מציג Top sectors
python scripts/sector_rotation.py

# עם תאריך ופרמטרים
python scripts/sector_rotation.py --end-date 2026-03-02 --lookback 6 --top 3 --out storage/sector_rotation.json
```

### תצורה

`config/symbols.yaml` → `sector_etfs: [XLK, XLV, XLF, XLE, XLI, XLY, XLP, XLU, XLB]`

---

## 6. best_combo_extended — שילוב כל האסטרטגיות

### מה

best_combo + Dual Momentum + Short-Term Reversal + Low-Vol Tilt.

### דגל

```bash
python scripts/run_backtest.py --mode best_combo_extended --period 3y
```

---

## 7. פקודות סיכום

```bash
# Multi-Universe
python scripts/run_multi_universe.py --period 3y --limit 10

# כל האסטרטגיות המורחבות
python scripts/run_backtest.py --mode best_combo_extended --period 3y

# Paper עם כל השכבות
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --dual-momentum --short-term-reversal --low-vol-tilt --dry-run

# Sector Rotation
python scripts/sector_rotation.py --top 3 --out storage/sector_rotation.json
```

---

## 8. תוצאות ראשוניות (לעדכון)

| מצב | Period | Sharpe | Return | Max DD | הערות |
|-----|--------|--------|--------|--------|-------|
| best_combo | 2y | ~1.9 | ~56% | ~-7.6% | בסיס |
| best_combo_extended | 2y | 0.27 | 2.4% | -12.5% | סינונים מחמירים — מקטינים trades |

**מסקנה:** Dual Momentum + STR Reversal + Low-Vol Tilt מחמירים מאוד — מפחיתים תשואה. כדאי להפעיל בנפרד (דגל בודד) ולמדוד.

---

## 9. בדיקה עצמית

| בדיקה | פקודה |
|--------|--------|
| best_combo baseline | `python scripts/run_backtest.py --mode best_combo --period 3y` |
| best_combo_extended | `python scripts/run_backtest.py --mode best_combo_extended --period 3y` |
| השוואה | להשוות Sharpe, Return, Max DD בין השניים |
| Multi-Universe | `python scripts/run_multi_universe.py --limit 5` |
| Sector Rotation | `python scripts/sector_rotation.py` |

---

## 10. קבצים שנוספו/שונו

| קובץ | תפקיד |
|------|--------|
| `config/symbols.yaml` | universe (25 נכסים), sector_etfs |
| `models/rules/dual_momentum.py` | בדיקת absolute momentum |
| `models/rules/short_term_reversal.py` | בדיקת oversold |
| `scripts/run_multi_universe.py` | Backtest על universe |
| `scripts/sector_rotation.py` | דירוג sector ETFs |
| `backtesting/engine.py` | dual_momentum, short_term_reversal, low_vol_tilt |
| `scripts/paper_trading_daily.py` | דגלים חדשים |
| `scripts/run_backtest.py` | דגלים חדשים |
| `config/backtest_modes.json` | best_combo_extended |

---

*נוצר: 2026-03 — הרחבת אסטרטגיות לפי STOCK_UNIVERSE_AND_STRATEGIES_RESEARCH.md*
