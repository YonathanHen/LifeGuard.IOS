@echo off
cd /d "%~dp0\.."
REM Full: python scripts/slippage_sensitivity.py
REM Quick: python scripts/slippage_sensitivity.py --quick
python scripts/slippage_sensitivity.py --quick
pause
