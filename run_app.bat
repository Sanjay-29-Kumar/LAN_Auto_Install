@echo off
title LAN Software Automation System
echo.
echo ========================================
echo   LAN Software Automation System
echo ========================================
echo.
echo Starting application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "app.py" (
    echo ERROR: app.py not found
    echo Please make sure you're running this from the correct directory
    pause
    exit /b 1
)

REM Install dependencies if needed
echo Checking dependencies...
pip install -r requirements.txt >nul 2>&1

REM Start the application
echo Starting LAN Automation System...
python app.py

if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start
    echo Please check the error messages above
    pause
)

echo.
echo Application closed.
pause 