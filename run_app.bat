@echo off
title Drone Control Center
echo ====================================================
echo   DRONE CONTROL CENTER - GRADUATION PROJECT
echo ====================================================
echo.
cd /d "%~dp0\drone_control"

echo Launching Drone Control Application...
python main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application crashed or exited with error code %ERRORLEVEL%.
    pause
)
