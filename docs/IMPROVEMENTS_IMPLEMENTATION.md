# SignalFlow — 5 שיפורים (Circuit Breaker, DD-Throttle, Degradation, Walk-Forward, Event Filter)

*מימוש: דגלים, סקריפטים, תיעוד*

---

## 1. Circuit Breaker + Drawdown Throttle

### דגלים

**Paper Trading:**
```bash
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --circuit-breaker 0.15
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --drawdown-throttle
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --circuit-breaker 0.15 --drawdown-throttle
```

**Backtest:**
```bash
python scripts/run_backtest.py --mode best_combo_cb --period 3y
python scripts/run_backtest.py --mode best_combo --circuit-breaker 0.15 --drawdown-throttle --period 3y
```

### לוגיקה

| תנאי | פעולה |
|------|-------|
| Drawdown ≥ 15% (Circuit Breaker) | חוסם כניסות חדשות — position=0 |
| Drawdown ≥ 15% (Throttle) | מקטין פוזיציה ל־50% |
| Drawdown ≥ 10% (Throttle) | מקטין פוזיציה ל־75% |

### קבצים

- `models/rules/circuit_breaker.py`
- `scripts/paper_trading_daily.py` — פרמטרים: `--circuit-breaker`, `--drawdown-throttle`
- `backtesting/engine.py` — `circuit_breaker_pct`, `drawdown_throttle`

---

## 2. Strategy Degradation Check

### דגל

```bash
python scripts/strategy_degradation_check.py
python scripts/strategy_degradation_check.py --symbol AAPL --rolling-days 60 --min-sharpe 1.0
```

### לוגיקה

- מחשב Rolling Sharpe (60 ימים) מתשואות Paper
- אם Sharpe < סף (ברירת מחדל 1.0) — התראת Degradation

### הרצה מומלצת

שבועי או חודשי (cron / Task Scheduler).

---

## 3. Walk-Forward Validation

### דגל

```bash
python scripts/walk_forward_validation.py
python scripts/walk_forward_validation.py --symbol AAPL --train-months 24 --test-months 6 --out storage/walk_forward_results.json
```

### לוגיקה

- חלונות: train 24 חודשים, test 6 חודשים
- השוואת Sharpe ב-train vs full (train+test)

---

## 4. Event Calendar Filter

### דגל

```bash
# ברירת מחדל: מופעל. להשבית:
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --no-event-filter
```

### תצורה

`config/event_calendar.json`:
```json
{
  "global": ["2025-01-29", "2025-03-19"],
  "AAPL": ["2025-01-30", "2025-04-24"]
}
```

הוסף תאריכי earnings, FOMC, CPI ידנית או באמצעות סקריפט.

---

## 5. תוצאות (2026-03-17)

| מצב | Sharpe | Return | Max DD | הערות |
|-----|--------|--------|--------|-------|
| best_combo | 1.934 | 56.8% | -7.6% | בסיס (3y, end 2026-03-02) |
| best_combo_cb | 1.934 | 56.8% | -7.6% | Circuit Breaker 15% + DD-Throttle — תוצאות זהות כי DD לא הגיע ל־10% |

**מסקנה:** כש־Max DD קטן מ־10%, אין הבדל — המנגנונים לא נכנסים לפעולה. במצבי משבר (DD > 10%) הם יחסמו/יקטינו.

---

## סיכום פקודות

```bash
# Paper עם כל השיפורים
python scripts/paper_trading_daily.py --symbol AAPL --no-ml --circuit-breaker 0.15 --drawdown-throttle

# Backtest עם Circuit Breaker
python scripts/run_backtest.py --mode best_combo_cb --period 3y

# Strategy Degradation (שבועי)
python scripts/strategy_degradation_check.py --min-sharpe 1.0

# Walk-Forward (רבעוני)
python scripts/walk_forward_validation.py --out storage/walk_forward_results.json
```

---

*נוצר: 2026-03 — חלק מתהליך Path to Production*
