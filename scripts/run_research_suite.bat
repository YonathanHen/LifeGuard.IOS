@echo off
setlocal
cd /d "%~dp0.."
python scripts/run_research_suite.py %*
