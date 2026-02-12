@echo off
REM Start Local Monitoring System
REM This script activates the virtual environment and starts the monitoring system

echo Starting Local Monitoring System...
echo ==================================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create a virtual environment first:
    echo python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if required packages are installed
python -c "import watchdog" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Required packages not installed!
    echo Please install dependencies:
    echo pip install -r requirements.txt
    pause
    exit /b 1
)

REM Start the monitoring system
echo Starting monitoring system...
echo Press Ctrl+C to stop monitoring
echo.
python src/monitor.py

echo.
echo Monitoring system stopped.
pause