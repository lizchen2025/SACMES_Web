@echo off
setlocal enabledelayedexpansion

REM SACMES Agent Launcher

title SACMES Agent

set SCRIPT_DIR=%~dp0

echo ========================================
echo SACMES Local Agent
echo ========================================
echo.

REM Check if agent.py exists
if not exist "%SCRIPT_DIR%agent.py" (
    echo [ERROR] agent.py not found
    echo Expected location: %SCRIPT_DIR%agent.py
    echo.
    pause
    exit /b 1
)

REM Check if portable Python is installed
if not exist "%SCRIPT_DIR%sacmes_python\python.exe" (
    echo Portable Python environment not found.
    echo Running first-time setup...
    echo.

    if not exist "%SCRIPT_DIR%install_portable_python.bat" (
        echo [ERROR] Installer not found: install_portable_python.bat
        pause
        exit /b 1
    )

    call "%SCRIPT_DIR%install_portable_python.bat"

    if errorlevel 1 (
        echo.
        echo [ERROR] Installation failed
        pause
        exit /b 1
    )

    echo.
    echo Installation complete.
    echo.
)

REM Verify Python installation
if not exist "%SCRIPT_DIR%sacmes_python\python.exe" (
    echo [ERROR] Python executable not found after installation
    pause
    exit /b 1
)

echo Verifying dependencies...

REM Set environment variables for tkinter
set "TCL_LIBRARY=%SCRIPT_DIR%sacmes_python\tcl\tcl8.6"
set "TK_LIBRARY=%SCRIPT_DIR%sacmes_python\tcl\tk8.6"

REM Check tkinter
"%SCRIPT_DIR%sacmes_python\python.exe" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] tkinter not available
    echo Please reinstall by deleting the sacmes_python folder and running this script again.
    pause
    exit /b 1
)

REM Check socketio
"%SCRIPT_DIR%sacmes_python\python.exe" -c "import socketio" >nul 2>&1
if errorlevel 1 (
    echo [WARN] python-socketio not found, installing...
    "%SCRIPT_DIR%sacmes_python\python.exe" -m pip install python-socketio requests --quiet
)

echo [OK] All dependencies verified
echo.

echo ========================================
echo Starting SACMES Agent
echo ========================================
echo.

"%SCRIPT_DIR%sacmes_python\python.exe" "%SCRIPT_DIR%agent.py"

set EXIT_CODE=%errorlevel%

echo.
echo ========================================
echo Agent Stopped
echo ========================================
echo.

if %EXIT_CODE% neq 0 (
    echo [ERROR] Agent exited with error code: %EXIT_CODE%
) else (
    echo Agent exited normally.
)

echo.
pause
