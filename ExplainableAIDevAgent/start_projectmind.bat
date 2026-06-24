@echo off
setlocal

echo Starting ProjectMind AI...
echo.

python run_projectmind.py
if %ERRORLEVEL% EQU 0 goto :end

echo.
echo Python launcher failed. Trying the Windows py launcher...
py -3 run_projectmind.py

:end
