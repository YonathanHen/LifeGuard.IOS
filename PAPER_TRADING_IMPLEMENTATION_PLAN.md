# SignalFlow — תוכנית יישום Paper Trading

*איך מיישמים את ה-Go/No-Go Framework הלכה למעשה*

---

## מה קיים היום

| רכיב | סטטוס | שימוש ל-Paper |
|------|--------|---------------|
| **API /predict/{symbol}** | ✔ | לוגיקת החלטה — Stat + Regime + Rules + ML |
| **BacktestEngine** | ✔ | סימולציית טריידים, Error Type Analysis |
| **run_backtest_with_ml.py --stability** | ✔ | Net EV, Sum Saved, Sum Missed, Blocked Loss Rate |
| **storage/backtest_runs.json** | ✔ | רישום אוטומטי |

**מה חסר:** רישום החלטות יומי־יומי בזמן אמת, ואיגוד מדדי Gate 2.

---

## ארכיטקטורה — 2 שכבות

### שכבה 1 — Daily Decision Logger (קל, חובה)

**מטרה:** כל יום לרשום מה המערכת אמרה — **בלי** לדעת עדיין את התוצאה.

| מדד | איך נאסף |
|-----|----------|
| **Exposure** | נגזר — % ימים עם has_edge=1 |
| **Decision Consistency** | נגזר — flip-flop יום־יומי |

**סקריפט:** `scripts/paper_trading_daily.py`

```
כל הרצה:
1. T = אתמול (או היום אם אחרי סגירה)
2. DataPipeline(symbol=AAPL, end_date=T)
3. הרצת לוגיקה כמו API: Stat, Regime, Rules, ML
4. שמירה ל-storage/paper_decisions.json:
   { date, has_edge_stat, has_edge_final, ml_blocked, regime, direction,
     stat_confidence, model_version, ml_probs, ... }
```

**Error Handling:** יום חסר ב-Logger = יום אבוד ב-Paper Trading. אם Yahoo/FRED נכשל — התראה (הדפסה, לוג, או מייל פשוט). לא להתעלם משגיאות בשקט.

**תזמון:** Task Scheduler / cron — לאחר סגירת השוק (למשל 22:00).

---

### שכבה 2 — Metrics Report (נדרש ל-Gate 2/3)

**מטרה:** לאפשר חישוב Blocked Loss Rate, Regret, Net EV.

**בעיה:** מדדים אלה דורשים ידיעת **תוצאה** — האם טרייד שחסמנו היה רווחי או מפסיד.

**פתרון:** הרצת BacktestEngine על **תקופת ה-Paper** (מתאריך ההתחלה עד אתמול). המנוע כבר מחשב:
- Stat-only: אילו טריידים היו
- Stat+ML: אילו נחסמו
- Error Type Analysis: sum_saved, sum_missed, net_ev, blocked_loss_rate

**סקריפט:** `scripts/paper_trading_report.py`

```
קלט: start_date (או מתאריך הרישום הראשון), end_date=אתמול
1. **בדיקת התאמה:** ודא שתאריכי הנתונים ב-Backtest (Yahoo) תואמים לתאריכים ב-paper_decisions — אין חריגות.
2. BacktestEngine.run(period מותאם)
3. engine.error_type_analysis() — מחזיר Blocked Loss Rate, Net EV
4. טעינת paper_decisions.json — Decision Consistency, Exposure, Average Holding Period
5. הדפסת דוח Gate 2 + השוואה לסף GO/NO-GO
```

**תזמון:** שבועי או חודשי — לא חייב יומי.

---

## מבנה קבצים

```
storage/
  paper_decisions.json   # החלטות יומיות (append)
  paper_metrics.json      # דוחות Gate 2 (לפי תאריך דוח)

scripts/
  paper_trading_daily.py   # הרצה יומית — רישום החלטה
  paper_trading_report.py  # דוח מדדי Gate 2
```

### פורמט paper_decisions.json

```json
[
  {
    "date": "2026-03-01",
    "symbol": "AAPL",
    "has_edge_stat": true,
    "has_edge_final": false,
    "ml_blocked": true,
    "regime": "trend",
    "direction": "up",
    "stat_confidence": "medium",
    "confidence_factors": {"cross_asset": true, "liquidity": true, ...},
    "ml_probs": {"P_up": 0.45, "P_down": 0.52},
    "model_version": "v1.2_safeguard_0.8"
  }
]
```

| שדה | מטרה |
|-----|------|
| **stat_confidence** | Score Rule Engine — לעזור להבין ב-Gate 2: ML חסם טרייד "גבולי" או "סיגנל חזק" |
| **model_version** | למשל `safeguard_0.8` או `lstm_2025-12` — אם תחליף מודל באמצע, תידע איזה תוצאות שייכות לאיזה גרסה |

### פורמט paper_metrics.json

```json
{
  "report_date": "2026-03-15",
  "period": {"start": "2026-01-01", "end": "2026-03-14"},
  "gate2": {
    "decision_consistency": 0.72,
    "avg_holding_period_days": 5.2,
    "blocked_loss_rate": 0.58,
    "net_ev": 0.012,
    "exposure_pct": 15.2
  },
  "go_no_go": "PENDING"
}
```

---

## סדר פיתוח מומלץ

| # | משימה | מאמץ | תלות |
|---|--------|------|------|
| 1 | **paper_trading_daily.py** | נמוך | אין — משתמש בלוגיקת API |
| 2 | **paper_decisions.json schema** | נמוך | 1 |
| 3 | **Task Scheduler / cron** | נמוך | 1 |
| 4 | **paper_trading_report.py** | בינוני | BacktestEngine.error_type_analysis |
| 5 | **שילוב Decision Consistency** | נמוך | 4 — חישוב מ-paper_decisions |
| 6 | **עדכון GO_NO_GO_FRAMEWORK** | נמוך | — קישור לסקריפטים |

---

## שימוש מתוכנן

```bash
# הרצה יומית (ידנית או cron)
python scripts/paper_trading_daily.py

# דוח Gate 2 (שבועי/חודשי)
python scripts/paper_trading_report.py
python scripts/paper_trading_report.py --start 2026-01-01 --end 2026-03-14
```

---

## הערות

1. **Decision Consistency** — חישוב: מתוך paper_decisions, כמה % ימים שבהם has_edge_final השתנה מ־יומו הקודם. flip-flop קיצוני = ערך נמוך. אם המערכת "מתחרטת" מהר מדי (Long→Flat→Long תוך ימים ספורים) — עמלות וסליפייג' יאכלו רווח. **Average Holding Period** — מדד משלים; עתיד: Hysteresis (מנגנון השהיה).
2. **Blocked Loss Rate, Net EV** — מגיעים מ־error_type_analysis של ה-backtest על התקופה. אין צורך בלוגיקה נוספת.
3. **Exposure** — יומי ממוצע מ־paper_decisions; או מ־backtest.
4. **משך מינימלי** — 3 חודשים לפני Gate 3. הדוח יציין "תקופה קצרה מדי" אם < 3 חודשים. **זה מונע החלטה אחרי שבועיים "מוצלחים" של מזל.**
5. **Data alignment** — ה-report מקפיד: תאריכי Yahoo = תאריכי paper_decisions. חריגות → אזהרה.

---

*גרסה 1.0 — 2026-03*
