# SignalFlow — מצבנו והדרך קדימה

*מסמך סטטוס: איפה אנחנו • מה חסר • מה לעשות*

**עודכן:** 2026-03-03

---

## 1. מצבנו — סיכום מנהלים

### 1.1 מה יש בידנו

| רכיב | סטטוס | פרטים |
|------|--------|--------|
| **Backtest 2y** | ✅ | Stat Sharpe 0.60, Stat+ML Sharpe **0.85**, תשואה 11.8% |
| **Backtest 5y** | ✅ | Stat Sharpe 0.17, Stat+ML Sharpe **0.19**, תשואה 7.3% |
| **Paper Trading** | ✅ | 126 ימי מסחר (6 חודשים) |
| **FRED Cache** | ✅ | פעיל — אין עוד rate limit |
| **Error Type Analysis** | ⚠️ | הושלם — Net EV=0 (אין חסימות ML ב־5y) |

### 1.2 מדדי Paper Trading (6 חודשים)

| מדד | ערך | משמעות |
|-----|-----|--------|
| Decision Consistency | 60.8% | שינויי החלטה מתונים — לא flip-flop |
| Exposure | 46% | כחצי מהימים בשוק |
| Avg Holding Period | 2.3 ימים | סגנון קצר־טווח |
| Gate 2 Go/No-Go | **NO-GO** | Blocked Loss Rate לא נמדד (0 חסימות) |

### 1.3 תוצאות Backtest 5 שנים

| מדד | Stat Only | Stat + ML |
|-----|-----------|-----------|
| Sharpe | 0.168 | **0.194** |
| Total Return | 5.6% | **7.3%** |
| Max Drawdown | -25.8% | -25.8% |
| By Regime (trend) | -0.10 | חלש |
| By Regime (mean_reverting) | 0.57 | **חזק** |

**Plateau:** תוצאות יציבות על Disaster Threshold 0.75–0.85 — מודל רובסטי.

---

## 2. מה חסר — לפני מעבר למסחר חי

| חסר | הסבר | חשיבות |
|-----|------|--------|
| **הוכחת ML חוסם** | 0 חסימות ב־5y — אין עדות ש־ML חוסם טריידים גרועים | גבוהה |
| **תקופת Paper מלאה** | 6 חודשים עבר מינימום; מומלץ 9 לפני Live | בינונית |
| **Gate 2 מלא** | Blocked Loss Rate, Net EV חיובי — תנאי ל־GO | גבוהה |
| **אימות regime trend** | Sharpe שלילי ב־trend — האסטרטגיה חלשה שם | נמוכה |

---

## 3. הדרך קדימה — צעדים מומלצים

### 3.1 עכשיו (0–4 שבועות)

| # | משימה | תדירות | כלי |
|---|--------|--------|-----|
| 1 | **הרצת Paper יומי** | כל יום אחרי סגירת שוק | `python scripts/paper_trading_daily.py` |
| 2 | **דוח Gate 2** | שבועי | `python scripts/paper_trading_report.py` |
| 3 | **בדיקת Error Type** | חודשי (2y / 3y) | `python scripts/run_backtest_with_ml.py --period 2y --stability` |

### 3.2 בינוני טווח (1–3 חודשים)

| # | משימה | מטרה |
|---|--------|------|
| 1 | **המשך Paper** לפחות עד 9 חודשים | מילוי תנאי Gate 3 |
| 2 | **עקיבה אחרי Blocked Loss Rate** | אם יופיעו חסימות — לבדוק Net EV |
| 3 | **Walk-Forward Retrain** (אם מודל מעל 90 יום) | `python scripts/walk_forward_retrain.py --check` |
| 4 | **תיעוד שינויים** | כל שינוי במודל/ספים — לרשום ולתארך |

### 3.3 תנאים למעבר ל-Live (Gate 3)

**לא** להתחיל מסחר חי עד שכל אלה מתקיימים:

- [ ] Paper Trading **לפחות 9 חודשים**
- [ ] **Blocked Loss Rate > 50%** או **Net EV ≥ 0** (אם יש חסימות)
- [ ] דוח Gate 2 מציג **GO**
- [ ] התחלה עם **גודל פוזיציה קטן** (כ־⅓ מהמתוכנן)

---

## 4. הרצות ופקודות

### יומית (Task Scheduler / cron)

```powershell
# Windows — להגדיר ב־Task Scheduler
$env:PYTHONIOENCODING="utf-8"
python scripts/paper_trading_daily.py
```

### שבועית

```powershell
python scripts/paper_trading_report.py --start 2025-09-01 --end 2026-03-02
```

### חודשית

```powershell
# Error Type על תקופות שונות
python scripts/run_backtest_with_ml.py --period 2y --stability
python scripts/run_backtest_with_ml.py --period 3y --stability
```

### Batch (הוספת היסטוריה)

```powershell
python scripts/paper_trading_daily.py --batch-start 2024-09-01 --batch-end 2025-08-28
```

---

## 5. ניתוח נוסף — תובנות והמלצות

### 5.1 "מלכודת 5 השנים"

ה-Sharpe הנמוך ב־5y (0.19) מול 2y (0.85) מראה שהאסטרטגיה **ילדת השוק השורי** של השנים האחרונות. בטווח הארוך ה־Stat Core מתקשה — מחזק את הצורך ב־ML כבלם זעזועים.

### 5.2 בעיית 0 חסימות

אם ב־5 שנים אין חסימות תחת סף 0.80:
- המודל LSTM "אופטימי" מאוד, או
- הנתונים המקרו (VIX, Yield Curve) לא הגיעו לערכי קיצון שמעוררים את ה-Negative Filter.

**משמעות:** המערכת כרגע היא למעשה **Stat Core במסווה של ML**.

### 5.3 היהלום — Regime Mean Reverting

ה-Sharpe של 1.01 ב־Mean Reverting הוא נקודת החוזק האמיתית של SignalFlow.

### 5.4 המלצות אופרטיביות — יושמו (2026-03-03)

| # | המלצה | סטטוס |
|---|--------|--------|
| 1 | **ניסוי סף נמוך (0.70)** | הרצה: `--disaster-threshold 0.70` |
| 2 | **הקטנת פוזיציה ב־Trend** | ✅ יושם ב־`backtesting/engine.py` — pos_mult=0.5 כש־regime=trend |
| 3 | **אוטומציה יומית** | ✅ `scripts/run_paper_trading_daily.bat` + `docs/TASK_SCHEDULER_SETUP.md` |

**ניסוי סף 0.70 — תוצאות:**
- Sharpe 0.243 (מול 0.194 ב־0.80)
- עדיין 0 חסימות — LSTM "אופטימי", לא מגיע ל־P_down>0.70

### 5.5 Baseline — הקפאה

**המסמך הזה מוכן להקפאה.** אל תשנה את קוד המודל — זהו baseline להשוואה.

---

## 6. שחזור (Reproducibility)

**קבצים לשמירה:**
- `storage/baseline_config.json` — פרמטרים מלאים (threshold, model, costs)
- `storage/lstm_model.pt` + `storage/lstm_model.json` — מודל LSTM
- `storage/backtest_runs.json` — היסטוריית הרצות
- `storage/paper_decisions.json` — החלטות Paper

**לעדכן baseline לפני שינויים:**
```powershell
python scripts/export_baseline.py
```

**לשחזר קוד:**
```powershell
git checkout b66513a   # או ה-commit שב-baseline_config.json
```

---

## 7. מסמכי ייחוס

| מסמך | תוכן |
|------|------|
| **GO_NO_GO_FRAMEWORK.md** | קריטריוני Gate 1/2/3 |
| **PAPER_TRADING_IMPLEMENTATION_PLAN.md** | ארכיטקטורת Paper Trading |
| **COMPREHENSIVE_TEST_REPORT.md** | תוצאות הבדיקה המקיפה |
| **PROGRESS_AND_NEXT_STEPS.md** | היסטוריה והתקדמות |

---

## 8. שורה תחתונה

| שאלה | תשובה |
|------|--------|
| **האם להתחיל לסחור?** | **לא.** עוד 3 חודשים Paper לפחות. |
| **מה המצב?** | המערכת מבטיחה — Backtest חיובי, Paper יציב, FRED Cache פעיל. חסר אישור מלא של Gate 2. |
| **מה הצעד הבא?** | להריץ Paper יומי, לפקח על דוחות Gate 2, ולהמתין ל־9 חודשים לפני החלטה על Live. |

---

*גרסה 1.0 — 2026-03-03*
