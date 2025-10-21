@echo off
REM SACMES Agent Launcher
REM This script automatically sets up and runs the SACMES local agent

setlocal enabledelayedexpansion

echo ========================================
echo SACMES Local Agent Launcher
echo ========================================
echo.

REM Check if Python directory exists
if not exist "python_embed" (
    echo Python environment not found. Running first-time setup...
    echo.
    call install_python.bat
    if errorlevel 1 (
        echo.
        echo ERROR: Setup failed. Please check your internet connection and try again.
        pause
        exit /b 1
    )
)

REM Check if agent.py exists
if not exist "agent.py" (
    echo ERROR: agent.py not found!
    echo Please ensure all files are extracted correctly.
    pause
    exit /b 1
)

REM Run the agent
echo Starting SACMES Agent...
echo.
python_embed\python.exe agent.py

REM If agent exits, pause to show any errors
if errorlevel 1 (
    echo.
    echo Agent exited with error. See messages above.
    pause
)
