# SignalFlow — תוצאות השוואת אסטרטגיות

*נוצר אוטומטית על ידי `scripts/run_strategy_compare.py`*

**שחזור תוצאות:** `docs/REPRODUCIBILITY.md` | **Path to Production:** `docs/PATH_TO_PRODUCTION.md` | עמלות (5+3 bps).

---

## אסטרטגיות משולבות (Combinations)

| שילוב | Sharpe | Return | Max DD | דגלים |
|-------|--------|--------|--------|-------|
| MR x2 + ATR Stop + Vol | **1.986** | 62.9% | -7.6% | `--mean-rev-mult 2.0 --atr-stop 2 --vol-target 0.15` |
| MR x2 + ATR Stop | 1.744 | **77.2%** | -11.1% | `--mean-rev-mult 2.0 --atr-stop 2` |
| ATR Stop + Vol Target | 1.940 | 30.7% | **-5.2%** | `--atr-stop 2 --vol-target 0.15` |

## פקודות להרצה

```bash
# הרצת כל האסטרטגיות (כולל שילובים)
python scripts/run_strategy_compare.py --period 3y --end-date 2026-03-02

# אסטרטגיה בודדת
python scripts/run_backtest.py --mode stat_only --period 3y --mean-rev-mult 2.0

# השילוב המומלץ (MR x2 + ATR + Vol)
python scripts/run_backtest.py --mode stat_only --period 3y --mean-rev-mult 2.0 --atr-stop 2 --vol-target 0.15

# Multi-symbol
python scripts/run_strategy_compare.py --period 3y --symbols AAPL,SPY,QQQ
```

## דגלים זמינים (run_backtest.py)

| דגל | תיאור | ערך לדוגמה |
|-----|--------|------------|
| --mean-rev-mult | מכפיל Mean Reverting | 2.0 |
| --vol-target | יעד תנודתיות שנתית | 0.15 |
| --atr-stop | כפל ATR stop | 2.0 |
| --kelly-frac | Kelly fractional | 0.5 |
| --symbols | נכסים מרובים | AAPL,SPY,QQQ |


## Run 2026-03-17 11:06
Period: 3y | End: 2026-03-02
Symbol: AAPL

| Strategy | Sharpe | Return | Max DD | Trades | Params |
|----------|--------|--------|--------|--------|--------|
| Stat Only (baseline) | 1.617 | 35.2% | -8.5% | 154 | use_ml=False, mean_rev_mult=1.0 |
| MR x2 (mean_rev_mult=2.0) | 1.507 | 64.0% | -13.8% | 154 | use_ml=False, mean_rev_mult=2.0 |
| Volatility Target 15% | 1.713 | 26.5% | -6.3% | 154 | use_ml=False, vol_target_ann=0.15 |
| ATR Stop x2 | 1.775 | 38.2% | -7.0% | 154 | use_ml=False, atr_stop_mult=2.0 |
| Half Kelly sizing | 1.375 | 17.2% | -5.0% | 154 | use_ml=False, kelly_frac=0.5 |
| MR x2 + Vol Target | 1.760 | 52.3% | -9.6% | 154 | use_ml=False, mean_rev_mult=2.0, vol_tar |

## Run 2026-03-17 11:15
Period: 3y | End: 2026-03-02
Symbol: AAPL (multi: AAPL,SPY,QQQ)

| Strategy | Sharpe | Return | Max DD | Trades | Params |
|----------|--------|--------|--------|--------|--------|
| Stat Only (baseline) | 1.617 | 35.2% | -8.5% | 154 | use_ml=False, mean_rev_mult=1.0 |
| MR x2 (mean_rev_mult=2.0) | 1.507 | 64.0% | -13.8% | 154 | use_ml=False, mean_rev_mult=2.0 |
| Volatility Target 15% | 1.713 | 26.5% | -6.3% | 154 | use_ml=False, vol_target_ann=0.15 |
| ATR Stop x2 | 1.775 | 38.2% | -7.0% | 154 | use_ml=False, atr_stop_mult=2.0 |
| Half Kelly sizing | 1.375 | 17.2% | -5.0% | 154 | use_ml=False, kelly_frac=0.5 |
| MR x2 + Vol Target | 1.760 | 52.3% | -9.6% | 154 | use_ml=False, mean_rev_mult=2.0, vol_tar |
| Multi-symbol ['AAPL', 'SPY', 'QQQ'] | 1.231 | -42.5% | -9.4% | 672 | *תיקון נוסף בפורמולת חישוב* |

## סיכום מומלצות (AAPL 3y) — עודכן 2026-03-17

| יעד | אסטרטגיה | תוצאות | דגל |
|-----|-----------|--------|-----|
| **הכי טוב overall** | MR x2 + ATR + Vol | Sharpe **1.99**, Return 62.9%, DD -7.6% | `--mean-rev-mult 2.0 --atr-stop 2 --vol-target 0.15` |
| Return מקסימלי | MR x2 + ATR Stop | 77.2%, DD -11.1% | `--mean-rev-mult 2.0 --atr-stop 2` |
| Sharpe מקסימלי | MR x2 + ATR + Vol | 1.986 | `--mean-rev-mult 2.0 --atr-stop 2 --vol-target 0.15` |
| DD מינימלי | ATR Stop + Vol | -5.2%, Sharpe 1.94 | `--atr-stop 2 --vol-target 0.15` |

## Run 2026-03-17 11:49
Period: 3y | End: 2026-03-02
Symbol: AAPL

| Strategy | Sharpe | Return | Max DD | Trades | Params |
|----------|--------|--------|--------|--------|--------|
| Stat Only (baseline) | 1.636 | 36.5% | -8.5% | 154 | horizon=daily, refit_every=5, commission |
| MR x2 (mean_rev_mult=2.0) | 1.545 | 68.4% | -13.8% | 154 | horizon=daily, refit_every=5, commission |
| Volatility Target 15% | 1.659 | 27.2% | -6.3% | 154 | horizon=daily, refit_every=5, commission |
| ATR Stop x2 | 1.827 | 40.1% | -7.0% | 154 | horizon=daily, refit_every=5, commission |
| Half Kelly sizing | 1.398 | 17.8% | -5.0% | 154 | horizon=daily, refit_every=5, commission |
| MR x2 + Vol Target | 1.679 | 54.6% | -9.6% | 154 | horizon=daily, refit_every=5, commission |
| MR x2 + ATR Stop | 1.744 | 77.2% | -11.1% | 154 | horizon=daily, refit_every=5, commission |
| ATR Stop + Vol Target | 1.940 | 30.7% | -5.2% | 154 | horizon=daily, refit_every=5, commission |
| MR x2 + ATR Stop + Vol Target | 1.986 | 62.9% | -7.6% | 154 | horizon=daily, refit_every=5, commission |

## Run 2026-03-17 12:03
Period: 5y
Symbol: AAPL

| Strategy | Sharpe | Return | Max DD | Trades | Params |
|----------|--------|--------|--------|--------|--------|
| Stat Only (baseline) | 0.819 | 38.7% | -12.6% | 360 | horizon=daily, refit_every=5, commission |
| MR x2 (mean_rev_mult=2.0) | 0.909 | 86.3% | -23.5% | 355 | horizon=daily, refit_every=5, commission |

## Run 2026-03-17 12:08
Period: 5y
Symbol: AAPL

| Strategy | Sharpe | Return | Max DD | Trades | Params |
|----------|--------|--------|--------|--------|--------|
| MR x2 + ATR Stop | 1.269 | 143.1% | -20.0% | 360 | horizon=daily, refit_every=5, commission |
| MR x2 + ATR Stop + Vol Target | 0.991 | 65.2% | -17.3% | 360 | horizon=daily, refit_every=5, commission |

## Run 2026-03-17 12:13
Period: 3y | End: 2026-03-02
Symbol: AAPL (multi: AAPL,SPY,QQQ)

| Strategy | Sharpe | Return | Max DD | Trades | Params |
|----------|--------|--------|--------|--------|--------|
| Stat Only (baseline) | 1.617 | 35.2% | -8.5% | 154 | horizon=daily, refit_every=5, commission |
| MR x2 + ATR Stop + Vol Target | 1.934 | 56.8% | -7.6% | 154 | horizon=daily, refit_every=5, commission |
| Multi-symbol ['AAPL', 'SPY', 'QQQ'] | 1.260 | 24.8% | -9.4% | 662 | commission_bps=5, slippage_bps=3, refit_ |
