# מה עובד — הרצת Universe (multi-symbol)

*מסמך ייחוס: מצבי `run_multi_universe.py` — **ברירת מחדל לא השתנתה**.*

---

## עקרון

- **ללא דגלים חדשים** — ההתנהגות נשארת **בדיוק** `best_combo` (כמו לפני השינוי).
- **`--profile production`** — מפעיל את אותם ברירות מחדל כמו `run_backtest_with_ml.py` (Stat+ML + Negative Filter).
- **`--low-vol-tilt` / `--dual-momentum`** — אופציונליים, מתווספים לכל פרופיל אם מועברים.

---

## מצבים

| פרופיל | פקודה לדוגמה | תיאור |
|--------|----------------|--------|
| **best_combo** (ברירת מחדל) | `python scripts/run_multi_universe.py --period 3y` | `use_ml=False`, mean_rev×2, ATR, vol target — **legacy** |
| **best_combo + low_vol** | `... --low-vol-tilt` | אותו פרופיל + הקטנת חשיפה בוול גבוה |
| **production** | `... --profile production --period 3y` | Stat+ML, `ml_negative_filter`, סף disaster 0.80 |
| **production Stat בלבד** | `... --profile production --no-ml` | בלי LSTM |
| **production + low_vol** | `... --profile production --low-vol-tilt` | כמו `run_backtest_with_ml --low-vol-tilt` לכל סימבול |

---

## פלט JSON

עם `--out path.json` נשמרים גם: `profile`, `low_vol_tilt`, `dual_momentum`, `no_ml`, `disaster_threshold`, `run_at`.

---

## קישורים

- `docs/HOT_UNIVERSE_PORTFOLIO_PLAN.md` — דירוג יקום (`rank_universe`) + `--from-rank-json` ב־`run_multi_universe` / `run_hot_ranked_backtest.py`
- `docs/RESEARCH_RUN_SUITE.md` — הרצת **כל** שילובי הפרופיל/דגלים בנפרד (`run_research_suite.py` + YAML)
- `docs/INSTITUTIONAL_DIRECTIONS_FEASIBILITY.md` — למה זה חשוב לחתך
- `docs/NEXT_EXECUTION_PLAN.md` — שלב 2 multi-symbol
- `docs/RESEARCH_DECISIONS_LOG.md` — לרשום תוצאות אחרי הרצה

---

*עדכון: פרופיל `production` + דגלים אופציונליים — הקיים נשמר כברירת מחדל.*
