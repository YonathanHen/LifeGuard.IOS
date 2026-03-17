# SignalFlow — תוצאות השוואת אסטרטגיות

*נוצר אוטומטית על ידי `scripts/run_strategy_compare.py`*

**שחזור תוצאות:** `docs/REPRODUCIBILITY.md` | כל התוצאות כוללות עמלות (5+3 bps).

---

## פקודות להרצה

```bash
# הרצת כל האסטרטגיות (רצף)
python scripts/run_strategy_compare.py --period 3y --end-date 2026-03-02

# אסטרטגיה בודדת
python scripts/run_backtest.py --mode stat_only --period 3y --mean-rev-mult 2.0

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

## סיכום מומלצות (AAPL 3y)

| יעד | אסטרטגיה | דגל |
|-----|-----------|-----|
| Return מקסימלי | MR x2 (64%) | `--mean-rev-mult 2.0` |
| Sharpe מקסימלי | ATR Stop (1.78) | `--atr-stop 2` |
| איזון Return+DD | MR x2 + Vol (52.3%, DD -9.6%) | `--mean-rev-mult 2.0 --vol-target 0.15` |
