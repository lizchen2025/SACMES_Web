@echo off
REM Simple debug runner - runs app_local.py directly with full terminal output
REM Use this instead of start.bat to see all error messages

title SACMES Local - Debug Mode

echo ============================================
echo SACMES Local Application - Debug Mode
echo ============================================
echo.
echo This will run the application with full terminal output
echo You will see all errors and debug messages in this window
echo.
echo To stop: Press Ctrl+C
echo.
echo ============================================
echo.

REM Find Python executable
set PYTHON_EXE=

REM Try python in PATH
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python
    goto :run_app
)

REM Try python3 in PATH
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python3
    goto :run_app
)

REM Try configured path
if exist python_path.txt (
    set /p PYTHON_EXE=<python_path.txt
    if exist "%PYTHON_EXE%" goto :run_app
)

echo ERROR: Python not found
echo.
echo Please ensure Python 3.9+ is installed and in PATH
echo Or create python_path.txt with path to python.exe
pause
exit /b 1

:run_app
echo Starting application with: %PYTHON_EXE%
echo.
echo ============================================
echo Application will start on http://localhost:5000
echo Open this URL in your browser
echo.
echo Press Ctrl+C to stop
echo ============================================
echo.

REM Run directly without browser auto-open
"%PYTHON_EXE%" app_local.py

echo.
echo ============================================
echo Application stopped
echo ============================================
pause
