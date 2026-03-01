# SignalFlow — Market Decision Support Platform

פלטפורמת תמיכה בהחלטות השקעה — יומי / שבועי / Regime Outlook.

ראה **PLANNING.md** למסמך ארכיטקטורה מלא.

---

## התקנה

```bash
pip install -r requirements.txt
```

## הפעלה

### 1. API (FastAPI)

```bash
cd SignalFlow
uvicorn api.main:app --reload --host 0.0.0.0
```

- Health: http://localhost:8000/health  
- Prediction: http://localhost:8000/predict/AAPL?horizon=daily  

### 2. Dashboard (Streamlit)

```bash
streamlit run dashboard/app.py
```

(דורש שה-API רץ ברקע.)

### 3. סקריפטים

```bash
python scripts/fetch_data.py
python scripts/run_backtest.py
```

### 4. טסטים

```bash
pytest tests/ -v
```

---

## מבנה הפרויקט

```
config/      — horizons.yaml, symbols.yaml
data/        — fetchers, preprocessing, features, pipeline
models/      — regime, stat (ARIMA, GARCH), rules (incl. cross_asset)
api/         — FastAPI
dashboard/   — Streamlit MVP
scripts/     — fetch_data
```

---

## Phase 1 — מה קיים

- [x] Data pipeline (Yahoo, resample, Z-score filter)
- [x] Stat Core (ARIMA + GARCH)
- [x] Regime Detector (HMM)
- [x] Cross-Asset Confirmation (VIX vs SP500)
- [x] Liquidity Gate (volume 20d avg)
- [x] Rule Engine (has_edge, confidence, system_assessment)
- [x] API endpoint /predict/{symbol}
- [x] Dashboard MVP (StatusBar, DecisionCard, Confidence)
- [x] Backtesting engine (Sharpe, max drawdown)

---

## SSL — Production Ready

המערכת משתמשת ב-**certifi** לבundle תקין של תעודות SSL. ברוב הסביבות החיבור עובד אוטומטית.

**רשתות מגבילות (Corporate proxy):** אם עדיין יש שגיאת SSL:
```powershell
$env:SIGNALFLOW_SSL_BYPASS="1"
```
לשימוש ברשתות עם פרוקסי/תעודות עצמיות בלבד.
