@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ========================================
REM SACMES Local Application Launcher
REM ========================================

title SACMES Local Application

set SCRIPT_DIR=%~dp0

echo.
echo ============================================
echo   SACMES Local Analysis System
echo   Starting...
echo ============================================
echo.

REM ----------------------------------------
REM 1. Check Python Environment
REM ----------------------------------------
echo [1/5] Checking Python environment...

REM Initialize Python executable path
set PYTHON_EXE=

REM Method 1: Check for embedded Python in local folder
if exist "%SCRIPT_DIR%python_embedded\python.exe" (
    echo [INFO] Found embedded Python in python_embedded\
    set PYTHON_EXE=%SCRIPT_DIR%python_embedded\python.exe
    goto :python_found
)

REM Method 2: Check for user-configured Python path
if exist "%SCRIPT_DIR%python_path.txt" (
    echo [INFO] Found python_path.txt configuration file
    set /p CUSTOM_PYTHON=<%SCRIPT_DIR%python_path.txt
    if exist "!CUSTOM_PYTHON!" (
        echo [INFO] Using configured Python: !CUSTOM_PYTHON!
        set PYTHON_EXE=!CUSTOM_PYTHON!
        goto :python_found
    ) else (
        echo [WARNING] Configured Python path not found: !CUSTOM_PYTHON!
    )
)

REM Method 3: Check for Python in system PATH
python --version >nul 2>&1
if !errorlevel! equ 0 (
    echo [INFO] Found Python in system PATH
    set PYTHON_EXE=python
    goto :python_found
)

REM Method 4: Check common Python installation locations
for %%p in (
    "C:\Python39\python.exe"
    "C:\Python310\python.exe"
    "C:\Python311\python.exe"
    "C:\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) do (
    if exist %%p (
        echo [INFO] Found Python at: %%p
        set PYTHON_EXE=%%~p
        goto :python_found
    )
)

REM Python not found - launch setup wizard
echo.
echo ============================================
echo [INFO] Python environment not found
echo ============================================
echo.
echo Launching Python setup wizard...
echo.
timeout /t 2 /nobreak >nul

REM Check if setup script exists
if exist "%SCRIPT_DIR%setup_python.bat" (
    call "%SCRIPT_DIR%setup_python.bat"

    REM After setup, retry detection
    if exist "%SCRIPT_DIR%python_path.txt" (
        echo.
        echo Setup completed. Restarting application...
        timeout /t 2 /nobreak >nul

        REM Restart this script
        "%~f0"
        exit /b 0
    ) else (
        echo.
        echo Setup cancelled or failed.
        pause
        exit /b 1
    )
) else (
    echo [ERROR] setup_python.bat not found!
    echo.
    echo Please download the complete SACMES Local package.
    pause
    exit /b 1
)

:python_found
REM Check Python version
for /f "tokens=2" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python version: %PYTHON_VERSION%
echo [OK] Python location: %PYTHON_EXE%

REM Validate version >= 3.9
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo [ERROR] Python version too low, need 3.9+
    pause
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 9 (
    echo [ERROR] Python version too low, need 3.9+
    pause
    exit /b 1
)

REM ----------------------------------------
REM 2. Check Core Files
REM ----------------------------------------
echo [2/5] Checking core files...

if not exist "%SCRIPT_DIR%app_local.py" (
    echo [ERROR] app_local.py not found
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%data_processing" (
    echo [ERROR] data_processing directory not found
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%static" (
    echo [ERROR] static directory not found
    pause
    exit /b 1
)

echo [OK] Core files complete

REM ----------------------------------------
REM 3. Check and Install Dependencies
REM ----------------------------------------
echo [3/5] Checking dependencies...

REM Check Flask
"%PYTHON_EXE%" -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [Installing] Flask...
    "%PYTHON_EXE%" -m pip install "Flask>=2.3.0,<3.0.0" --quiet --disable-pip-version-check
)

REM Check Flask-SocketIO
"%PYTHON_EXE%" -c "import flask_socketio" >nul 2>&1
if errorlevel 1 (
    echo [Installing] Flask-SocketIO...
    "%PYTHON_EXE%" -m pip install "Flask-SocketIO>=5.3.6" "python-socketio>=5.10.0" --quiet --disable-pip-version-check
)

REM Check NumPy
"%PYTHON_EXE%" -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo [Installing] NumPy...
    "%PYTHON_EXE%" -m pip install "numpy>=1.24.0,<2.0.0" --quiet --disable-pip-version-check
)

REM Check SciPy
"%PYTHON_EXE%" -c "import scipy" >nul 2>&1
if errorlevel 1 (
    echo [Installing] SciPy...
    "%PYTHON_EXE%" -m pip install "scipy>=1.10.0,<2.0.0" --quiet --disable-pip-version-check
)

REM Check watchdog
"%PYTHON_EXE%" -c "import watchdog" >nul 2>&1
if errorlevel 1 (
    echo [Installing] watchdog...
    "%PYTHON_EXE%" -m pip install "watchdog>=3.0.0" --quiet --disable-pip-version-check
)

echo [OK] All dependencies installed

REM ----------------------------------------
REM 4. Prepare Runtime Environment
REM ----------------------------------------
echo [4/5] Preparing runtime environment...

if not exist "%SCRIPT_DIR%uploads" mkdir "%SCRIPT_DIR%uploads"
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo [OK] Environment ready

REM ----------------------------------------
REM 5. Start Service
REM ----------------------------------------
echo [5/5] Starting SACMES Local service...
echo.
echo ============================================
echo   Service will start on: http://127.0.0.1:5000
echo   (If port 5000 is busy, another port will be used)
echo.
echo   Press Ctrl+C to stop the service
echo ============================================
echo.

REM Delay 3 seconds then open browser
start "" /B cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:5000"

REM Start Flask application
"%PYTHON_EXE%" "%SCRIPT_DIR%app_local.py"

set EXIT_CODE=%errorlevel%

REM ----------------------------------------
REM Cleanup and Exit
REM ----------------------------------------
echo.
echo ============================================
if %EXIT_CODE% EQU 0 (
    echo Service stopped normally
) else (
    echo [ERROR] Service exited with error code: %EXIT_CODE%
    echo.
    echo Check logs directory for details
)
echo ============================================
echo.
pause
