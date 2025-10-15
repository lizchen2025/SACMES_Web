@echo off
REM ============================================================
REM SACMES Agent Minimal EXE Builder
REM This script creates a minimal Python 3.8 environment and
REM packages agent.py into the smallest possible exe file
REM ============================================================

echo ============================================================
echo SACMES Agent EXE Builder - Minimal Version
echo ============================================================
echo.

REM Check if Python is available
echo [1/6] Checking for Python 3.8+...
python --version 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or later and ensure it's in your PATH.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

REM Create a clean virtual environment
echo [2/6] Creating minimal Python 3.8 virtual environment...
if exist agent_build_env (
    echo Removing old build environment...
    rmdir /s /q agent_build_env
)
python -m venv agent_build_env
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo OK: Virtual environment created
echo.

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call agent_build_env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo OK: Virtual environment activated
echo.

REM Install minimal dependencies
echo [4/6] Installing minimal dependencies...
pip install --no-cache-dir "python-socketio>=5.0.0,<6.0.0" "requests>=2.25.0"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pip install --no-cache-dir python-socketio requests
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)
echo.

REM Install PyInstaller
echo Installing PyInstaller for packaging...
pip install --no-cache-dir pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)
echo OK: Dependencies installed
echo.

REM Build the EXE with minimal options
echo [5/6] Building minimal EXE with PyInstaller...

REM Kill any running agent processes
taskkill /F /IM "SACMES_Agent*.exe" 2>NUL
timeout /t 1 >NUL

echo This may take a few minutes...
echo.

pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "SACMES_Agent" ^
    --icon "Netzlab.ico" ^
    --clean ^
    --strip ^
    --noupx ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module IPython ^
    --exclude-module notebook ^
    --exclude-module pytest ^
    --exclude-module setuptools ^
    agent.py

if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)
echo OK: EXE built successfully
echo.

REM Show results
echo [6/6] Build complete!
echo ============================================================
echo.
if exist dist\SACMES_Agent.exe (
    echo SUCCESS! Your minimal agent EXE has been created:
    echo Location: dist\SACMES_Agent.exe
    echo.
    for %%A in (dist\SACMES_Agent.exe) do (
        echo File size: %%~zA bytes ^(~%%~zA / 1024 / 1024 MB^)
    )
    echo.
    echo You can now:
    echo 1. Test the EXE by running: dist\SACMES_Agent.exe
    echo 2. Distribute this single file to users
    echo 3. Delete the agent_build_env folder to save space
    echo.
) else (
    echo ERROR: EXE file was not created!
    echo Please check the build output above for errors.
)

echo ============================================================
echo.
echo Press any key to exit...
pause >nul
