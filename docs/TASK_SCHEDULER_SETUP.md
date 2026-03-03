# SignalFlow — הגדרת Task Scheduler (Paper Trading יומי)

## Windows

### 1. פתח Task Scheduler

`Win + R` → `taskschd.msc` → Enter

### 2. צור משימה חדשה

- **Actions** → **Create Basic Task**
- **Name:** `SignalFlow Paper Trading Daily`
- **Description:** Runs paper_trading_daily.py after market close

### 3. Trigger — יומי

- **Trigger:** Daily
- **Start:** היום
- **Recur every:** 1 days
- **Time:** 23:00 (או שעה אחרי סגירת השוק)

### 4. Action — הרצת הסקריפט

**Action:** Start a program

**Program/script:**
```
C:\Users\Yonat\PycharmProjects\SignalFlow\scripts\run_paper_trading_daily.bat
```

**Start in:** (השאר ריק או)
```
C:\Users\Yonat\PycharmProjects\SignalFlow
```

### 5. תנאים (אופציונלי)

- **Run only when user is logged on** — אם המחשב כבוי בשעה 23:00, המשימה תרוץ בפעם הבאה שהמחשב יהיה דלוק ו־Task Scheduler ינסה שוב.

- או: **Run whether user is logged on or not** — רצה גם כשהמשתמש לא מחובר.

### 6. בדיקה

לחץ **Run** על המשימה ליד המקום → בדוק `storage/paper_decisions.json` שנווסף תאריך.

---

## Linux / Mac (cron)

```bash
# ערוך crontab
crontab -e

# הוסף שורה — הרצה יומית ב־23:00
0 23 * * * cd /path/to/SignalFlow && PYTHONIOENCODING=utf-8 python scripts/paper_trading_daily.py >> storage/paper_daily.log 2>&1
```

---

*נוצר: 2026-03-03*
