@echo off
REM SignalFlow - Paper Trading Daily (for Task Scheduler)
REM Run daily after market close (e.g. 23:00)
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
python scripts/paper_trading_daily.py
if errorlevel 1 (
    echo Paper trading daily failed >> storage\paper_daily.log 2>&1
)
