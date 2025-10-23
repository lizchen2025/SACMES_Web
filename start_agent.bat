@echo off
REM SACMES Agent Launcher
REM This script automatically sets up and runs the SACMES local agent

setlocal enabledelayedexpansion

REM Get the directory where this bat file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo SACMES Local Agent Launcher
echo ========================================
echo.
echo Working directory: %CD%
echo.

REM Check if Python directory exists
if not exist "%SCRIPT_DIR%sacmes_python" (
    echo Python environment not found. Running first-time setup...
    echo.

    REM Check if install_python.bat exists
    if not exist "%SCRIPT_DIR%install_python.bat" (
        echo ERROR: install_python.bat not found in %SCRIPT_DIR%
        echo Please ensure all files are extracted correctly.
        pause
        exit /b 1
    )

    echo Calling installer from: %SCRIPT_DIR%install_python.bat
    call "%SCRIPT_DIR%install_python.bat"

    if errorlevel 1 (
        echo.
        echo ERROR: Setup failed. Check install_log.txt for details.
        echo Log file location: %SCRIPT_DIR%install_log.txt
        pause
        exit /b 1
    )
)

REM Check if agent.py exists
if not exist "%SCRIPT_DIR%agent.py" (
    echo ERROR: agent.py not found!
    echo Expected location: %SCRIPT_DIR%agent.py
    echo Please ensure all files are extracted correctly.
    pause
    exit /b 1
)

REM Run the agent
echo Starting SACMES Agent...
echo.
"%SCRIPT_DIR%sacmes_python\python.exe" "%SCRIPT_DIR%agent.py"

REM If agent exits, pause to show any errors
if errorlevel 1 (
    echo.
    echo Agent exited with error. See messages above.
    pause
)
