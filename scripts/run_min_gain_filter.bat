@echo off
cd /d "%~dp0\.."
REM Requires trained LSTM: python scripts/train_lstm.py
python scripts/min_gain_filter.py --quick
pause
