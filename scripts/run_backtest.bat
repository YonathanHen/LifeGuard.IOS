@echo off
cd /d "%~dp0\.."
REM Default: stat_only (the proven profitable mode)
REM Try: python scripts/run_backtest.py --mode ml_threshold_050
REM List: python scripts/run_backtest.py --list-modes
python scripts/run_backtest.py
pause
