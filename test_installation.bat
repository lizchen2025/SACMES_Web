@echo off
REM SACMES Agent Installation Test
REM This script verifies that the Python installation is working correctly

echo ========================================
echo SACMES Agent Installation Test
echo ========================================
echo.

REM Check if Python directory exists
if not exist "sacmes_python" (
    echo ERROR: Python environment not found
    echo Please run start_agent.bat first to install Python
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking Python executable...
if not exist "sacmes_python\python.exe" (
    echo ERROR: python.exe not found
    echo Installation may be incomplete
    pause
    exit /b 1
)
echo OK: python.exe found

echo.
echo [2/4] Testing Python version...
sacmes_python\python.exe --version
if errorlevel 1 (
    echo ERROR: Python is not working correctly
    pause
    exit /b 1
)
echo OK: Python is working

echo.
echo [3/4] Testing required packages...
echo.
echo Checking python-socketio...
sacmes_python\python.exe -m pip show python-socketio >nul 2>&1
if errorlevel 1 (
    echo ERROR: python-socketio not installed
    echo Try running: install_python.bat
    pause
    exit /b 1
)
echo OK: python-socketio installed

echo.
echo Checking requests...
sacmes_python\python.exe -m pip show requests >nul 2>&1
if errorlevel 1 (
    echo ERROR: requests package not installed
    echo Try running: install_python.bat
    pause
    exit /b 1
)
echo OK: requests installed

echo.
echo [4/4] Testing tkinter (GUI support)...
sacmes_python\python.exe -c "import tkinter; print('OK: tkinter available')" 2>nul
if errorlevel 1 (
    echo WARNING: tkinter not available
    echo This means GUI features may be limited
    echo This is normal for embeddable Python installations
) else (
    sacmes_python\python.exe -c "import tkinter; print('OK: tkinter available')"
)

echo.
echo ========================================
echo Test Complete
echo ========================================
echo.
echo All required components are installed!
echo You can now run start_agent.bat
echo.
pause
