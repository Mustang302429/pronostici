@echo off
cd /d %~dp0
where py >nul 2>nul && (py -m motore.genera) || (python -m motore.genera)
pause
