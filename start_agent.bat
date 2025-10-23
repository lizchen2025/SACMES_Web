@echo off
REM SACMES Agent Launcher v4.0
REM This script automatically sets up and runs the SACMES local agent

REM Get the directory where this bat file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo SACMES Local Agent Launcher
echo ========================================
echo.
echo Working directory: %CD%
echo Script location: %SCRIPT_DIR%
echo.
pause

REM Check if Python directory exists
if not exist "%SCRIPT_DIR%sacmes_python" (
    echo [!] Python environment not found.
    echo [*] Running first-time setup...
    echo.

    REM Check if install_python.bat exists
    if not exist "%SCRIPT_DIR%install_python.bat" (
        echo [ERROR] install_python.bat not found in:
        echo %SCRIPT_DIR%
        echo.
        echo Please ensure all files are extracted correctly.
        echo.
        pause
        exit /b 1
    )

    echo [*] Calling installer: %SCRIPT_DIR%install_python.bat
    echo.
    call "%SCRIPT_DIR%install_python.bat"

    if errorlevel 1 (
        echo.
        echo [ERROR] Setup failed!
        echo.
        echo Check the log file for details:
        echo %SCRIPT_DIR%install_log.txt
        echo.
        pause
        exit /b 1
    )

    echo.
    echo [OK] Python installation complete!
    echo.
)

REM Check if agent.py exists
echo [*] Checking for agent.py...
if not exist "%SCRIPT_DIR%agent.py" (
    echo.
    echo [ERROR] agent.py not found!
    echo Expected location: %SCRIPT_DIR%agent.py
    echo.
    echo Please ensure all files are extracted correctly.
    echo.
    pause
    exit /b 1
)
echo [OK] agent.py found

REM Check if Python is installed
echo [*] Checking Python installation...
if not exist "%SCRIPT_DIR%sacmes_python\python.exe" (
    echo.
    echo [ERROR] Python executable not found!
    echo Expected: %SCRIPT_DIR%sacmes_python\python.exe
    echo.
    echo Python may not have installed correctly.
    echo Please delete the sacmes_python folder and run this script again.
    echo.
    pause
    exit /b 1
)
echo [OK] Python found

REM Run the agent
echo.
echo ========================================
echo Starting SACMES Agent...
echo ========================================
echo.

"%SCRIPT_DIR%sacmes_python\python.exe" "%SCRIPT_DIR%agent.py"

REM Capture exit code
set AGENT_EXIT=%errorlevel%

echo.
echo ========================================
echo Agent Stopped
echo ========================================
echo.

if %AGENT_EXIT% NEQ 0 (
    echo [ERROR] Agent exited with error code: %AGENT_EXIT%
    echo.
    echo Check the messages above for error details.
) else (
    echo [OK] Agent exited normally.
)

echo.
echo Press any key to close this window...
pause >nul
