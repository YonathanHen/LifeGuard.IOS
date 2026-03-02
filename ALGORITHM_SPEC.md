# SignalFlow — מפרט אלגוריתם ופרמטרים

*מסמך ייחוס: כל מרכיבי המערכת ופרמטרי ההרצה. לשיחזור ושיפור.*

---

## 1. ארכיטקטורה

| שכבה | רכיב | תיאור |
|------|------|--------|
| **Stat Core** | ARIMA + GARCH | חיזוי כיוון ותזמון תנודתיות |
| **Rule Engine** | has_statistical_edge, liquidity_gate, cross_asset | סף סטטיסטי + שערי סינון |
| **ML Safeguard** | LSTM + Negative Filter | חוסם כשהמודל חוזה P(down) > threshold |
| **Regime** | HMM (3 states) | trend / mean_reverting / high_volatility |

---

## 2. פרמטרים לפי רכיב

### 2.1 Data Pipeline
| פרמטר | ערך | מיקום |
|-------|-----|-------|
| symbol | AAPL (ברירת מחדל) | `DataPipeline(symbol=...)` |
| period | 5y / 3y / 2y | לפי סקריפט |
| horizon | daily / weekly / regime_outlook | `config/horizons.yaml` |

### 2.2 Horizons (`config/horizons.yaml`)
| horizon | resolution | z_score_window | cooldown_days | arima_order |
|---------|------------|----------------|---------------|-------------|
| daily | 1D | 30 | 3 | [2,0,2] |
| weekly | 1W | 20 | 7 | [2,0,1] |
| regime_outlook | 1M | 12 | — | — |

### 2.3 ARIMA
| פרמטר | ערך | מיקום |
|-------|-----|-------|
| order | (2, 0, 2) daily, (2,0,1) weekly | `backtesting/engine.py`, `config/horizons.yaml` |

### 2.4 GARCH
| פרמטר | ערך | מיקום |
|-------|-----|-------|
| garch_focus | risk_timing (daily), exposure_sizing (weekly), risk_regime (regime) | `config/horizons.yaml` |

### 2.5 Rule Engine
| פרמטר | תיאור |
|-------|--------|
| has_statistical_edge | AND: direction ≠ flat, volatility_bucket סביר, magnitude מספק |
| liquidity_gate | dollar_volume_20d מספיק |
| cross_asset | SP/VIX alignment |
| Forced Cooldown | אחרי regime shift, 3 ימים (daily) / 7 (weekly) |

### 2.6 LSTM (ML Layer)
| פרמטר | ערך | מיקום |
|-------|-----|-------|
| lookback | 40 (או 60) | `storage/lstm_model.json`, `walk_forward_retrain.py --lookback` |
| n_features | 4 | returns, vix, credit_spread, yield_curve |
| dropout | 0.3 | `models/ml/lstm_model.py` |
| Early Stopping | patience 15 | `walk_forward_retrain.py` |

### 2.7 ML Ensemble
| מצב | תיאור | threshold |
|-----|--------|-----------|
| **Negative Filter** (ברירת מחדל) | Trade = Stat Edge UNLESS P(down) > th | 0.80 |
| **Legacy AND** | Trade = Stat Edge AND P(up) ≥ th | 0.60 |

### 2.8 Backtest Engine
| פרמטר | ערך | מיקום |
|-------|-----|-------|
| refit_every | 5 ימים | `BacktestEngine(refit_every=5)` |
| train_min_days | 252 | `BacktestEngine(train_min_days=252)` |
| commission_bps | 5 | `--no-costs` מכבה |
| slippage_bps | 3 | `--no-costs` מכבה |
| round_trip_cost | 0.16% | 2×(5+3)/10000 |

### 2.9 Model Promotion
| תנאי | ערך |
|------|-----|
| Sharpe ≥ | 0.49 |
| Max DD ≤ | 12% |

---

## 3. תוצאות אחרונות (לרישום)

*Backtest נשמר אוטומטית ב־`storage/backtest_runs.json` | Validation → `storage/validation_runs.json`*

### 3.1 Backtest — Daily (AAPL 3y)

| מדד | Stat Core | Stat+ML (Neg Filter) |
|-----|-----------|----------------------|
| Sharpe | 1.756 | — |
| Max DD | -11.3% | — |
| Total Return | 52.9% | — |
| N Trades | 154 | — |
| Hit Rate | 58.4% | — |
| Exposure | 32.5% | — |

**לפי Regime:** trend 2.52/-6.5%/55 | mean_reverting 2.14/-6.0%/99 | high_vol 0.

*מקור: `storage/backtest_runs.json` — עדכון אוטומטי בכל הרצה.*

### 3.2 Validation — Daily / Weekly / Regime (Accuracy %)

| Horizon | Stat Core | Stat+ML | decisions |
|---------|-----------|---------|-----------|
| **daily** | 66.7% (12/18) | — (0 decisions, ML חסם הכל) | 40 samples |
| **weekly** | 40.6% (13/32) | 40.6% (13/32) | 40 samples |
| **regime_outlook** | — (0 valid) | — | 0 valid |
| **TOTAL** | 50.0% (25/50) | 40.6% (13/32) | — |

*מקור: `storage/validation_runs.json` (2026-03-02).*  
*הערה: daily — Legacy AND (P_up≥0.6) חסם את כל 18 ההחלטות של Stat.*

### 3.3 Error Type Analysis (עם `--stability`)

| מדד | ערך |
|-----|-----|
| Saved Losses | — |
| Missed Opportunities | — |
| Sum Saved | — |
| Sum Missed | — |
| Net EV of ML Filter | — |

---

## 4. פקודות לשיחזור

```bash
# Backtest יומי (ברירת מחדל)
python scripts/run_backtest_with_ml.py --period 3y

# Backtest יומי (נשמר אוטומטית)
python scripts/run_backtest_with_ml.py --period 3y --label baseline_2026

# Validation — daily / weekly / regime
python scripts/run_validation_with_ml.py

# Legacy AND (61.4% hit rate)
python scripts/run_backtest_with_ml.py --period 3y --no-negative-filter
```

---

## 5. קבצי תצורה מרכזיים

| קובץ | תפקיד |
|------|--------|
| `config/horizons.yaml` | פרמטרי daily/weekly/regime |
| `.env` | ML_NEGATIVE_FILTER_THRESHOLD, FRED_API_KEY |
| `storage/lstm_model.json` | lookback, n_features, train_date |
| `storage/backtest_runs.json` | היסטוריית Backtest (שמירה אוטומטית) |
| `storage/validation_runs.json` | היסטוריית Validation (daily/weekly/regime) |
| `RESULTS_SUMMARY.md` | סיכום מרוכז של כל התוצאות |

---

*גרסה 1.0 — 2026-03*
