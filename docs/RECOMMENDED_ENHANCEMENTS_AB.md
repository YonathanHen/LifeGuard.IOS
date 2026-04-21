# שיפורים מומלצים — פרוטוקול A/B ויישום

*מסמך משולב: מה ממליצים (מתוך roadmap + קטלוג), מה כבר בקוד, איך להשוות “עם / בלי”, ואיפה לרשום תוצאות.*

---

## 1. מה בודקים

| שיפור | משמעות | פרמטר ב־`BacktestEngine` |
|--------|--------|--------------------------|
| **Baseline** | Stat Core (או Stat+ML) בלי שכבות נוספות | — |
| **Dual momentum** | SPY: אם תשואת 12 חודשים < ריבית הפרעה (~4%) → לא נכנסים | `dual_momentum=True` |
| **Short-term reversal** | ב־mean_reverting: כניסה רק אם “מוכרים יותר מדי” (תשואה חודשית שלילית) | `short_term_reversal=True` |
| **Low-vol tilt** | כשתנודתיות בקוורטיל העליון (60 יום) → מקטינים חשיפה ב־0.5 | `low_vol_tilt=True` |
| **Momentum 12-1 (נכס)** | לונג רק אם מומנטום 12-1 חיובי (חלון ~252 יום, דילוג ~חודש) | `momentum_12_1_filter=True` |
| **All** | כל הארבעה יחד | כל הדגלים `True` |

---

## 2. מה נוסף בקוד

- **`momentum_12_1_filter`** ב־`backtesting/engine.py` — פילטר מומנטום בסגנון מחקר (12-1) על סדרת התשואות של הסימבול.
- **`scripts/run_enhancement_ab.py`** — מריץ את כל התרחישים ברצף ומדפיס טבלה + דלתא מול baseline.

---

## 3. איך להריץ (אצלך)

### סוללה מומלצת (רק מה שנראה מבטיח אחרי A/B הראשון)

`baseline` + `dual_momentum_spy` + `low_vol_tilt` + **שילוב של שניהם** (בלי short_term_reversal / 12-1).

```powershell
cd c:\Users\Yonat\PycharmProjects\SignalFlow

# Stat, 3y, refit רגיל (ללא --fast) — העדיפות לקבלת החלטה
python scripts/run_enhancement_ab.py --battery helpful --period 3y --symbol AAPL --json-out storage/enhancement_ab_helpful_3y_stat.json

# אותה סוללה עם Stat+ML (Negative Filter)
python scripts/run_enhancement_ab.py --battery helpful --period 3y --symbol AAPL --with-ml --json-out storage/enhancement_ab_helpful_3y_ml.json
```

### כל התרחישים (כולל אלה שהורידו ביצועים ב-2y fast)

```bash
cd c:\Users\Yonat\PycharmProjects\SignalFlow

# Stat בלבד — השוואה מלאה
python scripts/run_enhancement_ab.py --battery full --period 3y --symbol AAPL

# אותו דבר + Stat+ML (Negative Filter)
python scripts/run_enhancement_ab.py --battery full --period 3y --symbol AAPL --with-ml

# שמירת JSON לתיעוד
python scripts/run_enhancement_ab.py --battery full --period 3y --json-out storage/enhancement_ab_stat.json
```

**הערה:** כל הרצה גורמת לבקטסט מלא (כולל ML אם `--with-ml`) — יכול לקחת דקות.

**אם Yahoo Finance נכשל** (`NoneType`, ריק): עודכן `fetch_yahoo` — ניסיונות נוספים + גיבוי `yf.download`. נסי שוב אחרי דקה; ברשת ארגונית: `$env:SIGNALFLOW_SSL_BYPASS="1"`.

---

## 4. איך לפרש

- **Sharpe עולה + DD לא מחמיר בהרבה** → שיפור איכותי.
- **תשואה גולמית יורדת אבל DD יורד חד** → “investable” יותר, לא בהכרח “יותר רווח גולמי”.
- **אם כל השכבות יחד מחמירות** → אולי רק חלק מהן נשמרות; לבדוק כל אחת לבד (כבר מודפס בטבלה).

---

## 5. תוצאות ומסקנות רשמיות

**יומן החלטות (לא לשכוח):** [`RESEARCH_DECISIONS_LOG.md`](RESEARCH_DECISIONS_LOG.md) — רשומה #1 מתעדת את הרצת ה־helpful 3y (Stat+ML) ואת שמירת אופציית `low_vol_tilt`.

נתוני גולם: `storage/enhancement_ab_helpful_3y_ml.json` (ו־`*_stat.json` אם הורצה Stat בלבד).

---

## 6. קישורים

- `docs/ALGORITHMIC_STRATEGIES_CATALOG_RESEARCH.md`
- `docs/STRATEGY_RESEARCH_AND_RECOMMENDATIONS.md`
- `HEDGE_FUNDS_ANALYSIS_AND_ROADMAP.md`

---

*עדכון: יומן מסקנות ב־`RESEARCH_DECISIONS_LOG.md`; פרוטוקול A/B בקובץ זה.*
