@echo off
cd /d %~dp0
where py >nul 2>nul && (py -m pip install -r requirements.txt) || (python -m pip install -r requirements.txt)
pause
