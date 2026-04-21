# SignalFlow — סיכום כל התוצאות

*עדכון אחרון: 2026-03*

**ניתוח מקיף + Revert:** `storage/SUCCESS_HISTORY_AND_REVERT_ANALYSIS.md`

---

## 1. Backtest — Daily (AAPL 3y)

**מקור:** `storage/backtest_runs.json` | הרצה: `python scripts/run_backtest_with_ml.py --period 3y`

### Stat Core

| מדד | ערך |
|-----|-----|
| **Sharpe** | 1.756 |
| **Max Drawdown** | -11.3% |
| **Total Return** | 52.9% |
| **N Trades** | 154 |
| **Hit Rate** | 58.4% |
| **Exposure** | 32.5% |

### לפי Regime

| Regime | Sharpe | Max DD | Trades |
|--------|--------|--------|--------|
| trend | 2.52 | -6.5% | 55 |
| mean_reverting | 2.14 | -6.0% | 99 |
| high_volatility | 0 | 0% | 0 |

### פרמטרי הרצה

- symbol: AAPL
- period: 3y
- horizon: daily
- commission: 5 bps, slippage: 3 bps
- LSTM: lookback 40, n_features 4

---

## 2. Validation — Daily / Weekly / Regime (Accuracy)

**מקור:** `storage/validation_runs.json` | הרצה: `python scripts/run_validation_with_ml.py`

| Horizon | Stat Core | Stat+ML | הערות |
|---------|-----------|---------|-------|
| **daily** | 66.7% (12/18) | 0 decisions | ML (Legacy AND) חסם את כל ההחלטות |
| **weekly** | 40.6% (13/32) | 40.6% (13/32) | אין ML ל־weekly |
| **regime_outlook** | — | — | 0 valid samples |
| **TOTAL** | 50.0% (25/50) | 40.6% (13/32) | |

- 40 samples per horizon (point-in-time)
- daily: Stat יצר 18 החלטות, ML חסם את כולן (P_up < 0.6)
- weekly: Stat = Stat+ML (ללא שכבת ML)

---

## 3. תוצאות היסטוריות (מתוך PROGRESS)

| הרצה | Stat Core | Stat+ML | הערות |
|------|-----------|---------|-------|
| Stat + ML (Neg Filter) | Sharpe 1.73 | Sharpe 1.70 | DD -11.3%, ML כמעט לא מסנן |
| Stat + ML (Legacy AND) | 58.2% hit | **61.4% hit** | 70 trades, Sharpe 2.12, DD -3.6% |
| Validation 40 dates | 65% daily | 83% (6 decisions) | החלטות משמעותיות |

---

## 4. קבצי שמירה

| קובץ | תוכן |
|------|------|
| `storage/backtest_runs.json` | כל הרצות Backtest (שמירה אוטומטית) |
| `storage/validation_runs.json` | כל הרצות Validation |
| `storage/SUCCESS_HISTORY_AND_REVERT_ANALYSIS.md` | היסטוריית הצלחות + ניתוח Revert |
| `storage/PERFORMANCE_REPORT.md` | סימולציה 5y (27.8%, Regime Sizing) |
| `storage/LEVERAGE_ANALYSIS_AND_RECOMMENDATIONS.md` | MR x2 — 52.1% |
| `results/*.json` | תוצאות backtest לפי תאריך |
| `ALGORITHM_SPEC.md` | מפרט אלגוריתם + פרמטרים + תוצאות |
| `RESULTS_SUMMARY.md` | מסמך זה — סיכום מרוכז |
| **`docs/RESEARCH_DECISIONS_LOG.md`** | **יומן מסקנות מחקר** — החלטות A/B, תאריכים, קבצי JSON, שחזור |

---

## 5. פקודות להרצה

```bash
# Backtest (נשמר אוטומטית)
python scripts/run_backtest_with_ml.py --period 3y

# Validation — daily + weekly + regime (נשמר אוטומטית)
python scripts/run_validation_with_ml.py

# Legacy AND — 61.4% hit rate
python scripts/run_backtest_with_ml.py --period 3y --no-negative-filter
```

---

*SignalFlow — 2026-03*
