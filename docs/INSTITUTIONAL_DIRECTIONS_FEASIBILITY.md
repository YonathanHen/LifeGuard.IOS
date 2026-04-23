# כיוונים מוסדיים — איך לשלב ולבדוק היתכנות ב-SignalFlow

*תשובה מעשית לטבלת “ריבוי פקטורים / חתך / LTR / סיכון / חוסן” — בלי הבטחת רווח.*

מסמכים קשורים: `ALGORITHMIC_STRATEGIES_CATALOG_RESEARCH.md`, `NEXT_EXECUTION_PLAN.md`, `RESEARCH_DECISIONS_LOG.md`.

---

## 1. מפת היתכנות (סיכום)

| כיוון | מה כבר יש אצלנו | בדיקת היתכנות מינימלית | מה חסר ליישום “מלא” | סיכון עיקרי |
|--------|------------------|-------------------------|----------------------|--------------|
| **ריבוי פקטורים** | חוקים + Regime + אופציית `low_vol_tilt`, `dual_momentum`; מומנטום 12-1 ב-engine | להפעיל פקטור **אחד נוסף** בכל פעם + A/B (כמו low_vol) | משקלי גורמים, פורטפוליו לונג-שורט אקדמי | Overfitting אם מוסיפים הכל בבת אחת |
| **אופטימיזציה חתכית** | `config/symbols.yaml` + `scripts/run_multi_universe.py` | הרצת universe עם **אותה לוגיקה** על כל סימבול (ראו סעיף 2) | דירוג יומי/שבועי, בחירת Top-K, מקס סימבולים | עלות מחשוב; שונה מ-`run_multi_universe` הנוכחי |
| **Learning-to-rank / ML על פקטורים** | LSTM נקודתי; לא LTR | שלב 1: **דירוג לפי ציון פשוט** (למשל מומנטום 12-1) בלי רשת | מודל LTR + אימון + walk-forward | Overfitting, דליפת מידע |
| **ניהול סיכון שיטתי** | Rule engine, ML safeguard, עלויות בבקטסט, `low_vol_tilt` | המשך Paper + Gate 2 | תקרות תיק, וריאציות sizing | — |
| **חוסן ברגימה** | Regime HMM, cooldown, cross-asset | בקטסט על **כמה חלונות** (שנים שונות); `--period 5y` | פחות פרמטרים, Plateau | תקופה אחת “מטעה” |

---

## 2. חתך (Cross-section) — הכי קרוב למה שיש היום

### מה יש
- **`scripts/run_multi_universe.py`** — עובר על רשימת `universe` ומריץ `BacktestEngine` **לכל סימבול בנפרד**.
- **ברירת מחדל:** עדיין **`best_combo`** (לא השתנה).
- **`--profile production`:** אותה לוגיקה כמו `run_backtest_with_ml.py` (Stat+ML + Negative Filter), עם `--low-vol-tilt` / `--dual-momentum` / `--no-ml` אופציונליים.

**תיעוד מצבים:** [`WORKING_MULTI_UNIVERSE_PROFILES.md`](WORKING_MULTI_UNIVERSE_PROFILES.md)

### בדיקת היתכנות שלב א’ (מומלץ)
**מטרה:** לראות אם **אותה אסטרטגיה** (למשל Stat+ML + low_vol) **מתנהגת בצורה דומה** על כמה מניות בלי tuning.

**אופציה א’ — סקריפט universe (מומלץ):**

```powershell
python scripts/run_multi_universe.py --profile production --period 3y --limit 10 --low-vol-tilt --out storage/multi_prod_lowvol_3y.json
```

**אופציה ב’ — ידני (סימבול-סימבול):**

```powershell
foreach ($s in "SPY","QQQ","MSFT","GOOGL","JPM") {
  python scripts/run_backtest_with_ml.py --period 3y --symbol $s --low-vol-tilt --label "lowvol_${s}_3y"
}
```

### שלב ב’ (עתידי): דירוג Top-K
- בכל יום (או שבוע): להריץ pipeline **נקודתי** על כל סימבול ב-universe → לקבל ציון (למשל הסתברות / edge בינארי).
- ללכת **לונג** על ה-K הראשונים במשקל שווה או לפי ציון.
- **לא מיושם היום** — זה שכבת פורטפוליו חדשה (מחוץ ל-backtest של נכס יחיד).

---

## 3. ריבוי פקטורים (Momentum / Value / Quality)

### בדיקת היתכנות
- **מומנטום:** כבר יש `momentum_12_1_filter` ו־`dual_momentum` — לבדוק ב־`run_enhancement_ab --battery full` או דגלים ב־engine; **רק אם A/B מראה שיפור** (אצלכם 12-1 על הנכס הוריד ב-2y fast).
- **Value / Quality:** דורש נתוני פנדמנטלס (או פרוקסי פשוטים) — לא ב-pipeline היומי.  
  **MVP:** גרסה “דלילה” — למשל **P/E או Market Cap** מ-Yahoo — רק אחרי בדיקת נקיון (look-ahead, תדירות עדכון).

### סדר עבודה מומלץ
1. פקטור אחד → A/B → רשומה ב־`RESEARCH_DECISIONS_LOG.md`.  
2. רק אחרי Paper חיובי — פקטור שני.

---

## 4. Learning-to-rank (LTR)

### בדיקת היתכנות שלב א’ — בלי ML
- **דירוג יחסי:** בכל תאריך, לכל סימבול ב-universe: ציון = מומנטום 12-1 או “יש Stat edge” (0/1).  
  בחרי **Top 3** — סימולציה ידנית או סקריפט קטן ששומר רק את התשואה המשולבת.
- אם זה **לא** יציב — LTR עם רשת לא יפתור.

### שלב ב’ — ML
- רק אחרי שלב א’ + Paper; עם walk-forward ומעט פרמטרים.

---

## 5. ניהול סיכון וחוסן ברגימה

### כבר משולב
- כללי כניסה/יציאה, עלויות, ML safeguard, Regime, `low_vol_tilt` (אופציונלי).

### בדיקות נוספות
- **כמה חלונות זמן:** `3y` מול `5y` על אותה תצורה.  
- **Plateau ספים:** `run_backtest_with_ml.py --stability`.  
- **Paper:** התנהגות בזמן אמת לעומת בקטסט.

---

## 6. מקורות חיצוניים (לקריאה)

- סקירות multi-factor / cross-section — RePEc / arXiv (מזכירים בקטלוג).  
- סקירות אסטרטגיות כמותיות — מקורות כמו TunedAlpha (המחישו עקרונות, לא העתקה ישירה).  
- דיון ב-robustness — דוחות מוסדיים (למשל Gresham) על שבירת מתאמים ומדיניות.

**לא מייבאים מספרי תשואה מהמאמרים ישירות ל-AAPL יומי.**

---

## 7. צעד הבא המומלץ בפרויקט (קונקרטי)

1. **`run_multi_universe.py --profile production --low-vol-tilt --limit 10`** + `--out storage/....json`.  
2. לתעד ממוצע/חציון Sharpe ו-DD ב־`RESEARCH_DECISIONS_LOG.md` (רשומה #2).  
3. שלב **Top-K / דירוג חתכי** — עדיין עתידי; ראו סעיף 2 “שלב ב’”.

---

*מסמך זה מתאר **היתכנות ובדיקות** — לא החלטת מסחר.*
