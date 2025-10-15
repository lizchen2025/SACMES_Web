@echo off
REM Build SACMES Agent with Console Window for Debugging
REM This version shows console output to help diagnose connection issues

echo ============================================================
echo SACMES Agent Console EXE Builder (Debug Version)
echo ============================================================
echo.

echo [1/6] Checking for Python...
python --version 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo.

echo [2/6] Creating virtual environment...
if exist agent_build_env (
    echo Removing old build environment...
    rmdir /s /q agent_build_env
)
python -m venv agent_build_env
call agent_build_env\Scripts\activate.bat
echo.

echo [3/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo.

echo [4/6] Installing dependencies...
pip install --no-cache-dir "python-socketio>=5.0.0,<6.0.0" "requests>=2.25.0"
if %errorlevel% neq 0 (
    echo Trying any available version...
    pip install --no-cache-dir python-socketio requests
)
echo.

pip install --no-cache-dir pyinstaller
echo.

echo [5/6] Cleaning previous builds...

REM Kill any running agent processes
taskkill /F /IM "SACMES_Agent*.exe" 2>NUL
timeout /t 1 >NUL

REM Clean build directories
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

echo [6/6] Building console EXE for debugging...
echo.

pyinstaller --noconfirm ^
    --onefile ^
    --console ^
    --name "SACMES_Agent_Debug" ^
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
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.

if exist dist\SACMES_Agent_Debug.exe (
    echo SUCCESS! Debug console EXE created:
    echo Location: dist\SACMES_Agent_Debug.exe
    echo.
    for %%A in (dist\SACMES_Agent_Debug.exe) do (
        set /a size_mb=%%~zA / 1024 / 1024
        echo File size: %%~zA bytes (~!size_mb! MB)
    )
    echo.
    echo This version includes:
    echo - Console window showing all debug output
    echo - Socket.IO connection logs
    echo - Error messages and tracebacks
    echo - Netzlab icon
    echo.
    echo Use this version to diagnose connection problems!
    echo.
) else (
    echo ERROR: EXE was not created
)

pause
