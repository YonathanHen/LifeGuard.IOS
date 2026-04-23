@echo off
cd /d "%~dp0\.."
REM Verify threshold 0.85 works on AAPL, MSFT, GOOGL (not overfitting)
python scripts/ml_threshold_stability.py --threshold 0.85
pause
