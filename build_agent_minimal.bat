@echo off
REM ============================================================
REM SACMES Agent Ultra-Minimal EXE Builder (Using .spec file)
REM Creates the absolute smallest possible EXE
REM ============================================================

echo ============================================================
echo SACMES Agent Ultra-Minimal EXE Builder
echo Using optimized PyInstaller spec file
echo ============================================================
echo.

REM Check if Python 3.8+ is available
echo [1/6] Checking for Python 3.8+...
python --version 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or later.
    pause
    exit /b 1
)
python --version
echo.

REM Create a clean virtual environment
echo [2/6] Creating minimal virtual environment...
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

REM Upgrade pip to latest version
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo.

REM Install minimal dependencies
echo [5/6] Installing minimal dependencies...
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

echo Installing PyInstaller for packaging...
pip install --no-cache-dir pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)
echo OK: Dependencies installed
echo.

REM Clean previous builds
echo [6/6] Cleaning previous builds...

REM Kill any running agent processes
taskkill /F /IM "SACMES_Agent*.exe" 2>NUL
timeout /t 1 >NUL

REM Clean build directories
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
echo.

REM Build using the optimized spec file
echo Building ultra-minimal EXE using spec file...
echo This may take 2-3 minutes...
echo.

pyinstaller --clean agent_minimal.spec

if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)
echo.

REM Show results
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
if exist dist\SACMES_Agent_Minimal.exe (
    echo SUCCESS! Your ultra-minimal agent EXE has been created:
    echo.
    echo Location: dist\SACMES_Agent_Minimal.exe
    echo.

    REM Calculate file size in MB
    for %%A in (dist\SACMES_Agent_Minimal.exe) do (
        set size=%%~zA
        set /a size_mb=%%~zA / 1024 / 1024
        echo File size: %%~zA bytes ^(~!size_mb! MB^)
    )
    echo.
    echo ============================================================
    echo Next Steps:
    echo ============================================================
    echo 1. Test the EXE: dist\SACMES_Agent_Minimal.exe
    echo 2. Distribute this single file to users
    echo 3. Optional: Delete agent_build_env folder to save space
    echo    ^(Run: rmdir /s /q agent_build_env^)
    echo.
    echo The EXE includes:
    echo   - Full GUI interface
    echo   - Socket.IO connectivity
    echo   - File monitoring system
    echo   - All necessary Python runtime
    echo.
    echo No Python installation needed on target machines!
    echo ============================================================
) else (
    echo ERROR: EXE file was not created!
    echo Please check the build output above for errors.
    echo.
    echo Common issues:
    echo - Missing dependencies
    echo - Antivirus blocking PyInstaller
    echo - Insufficient disk space
)
echo.
echo Press any key to exit...
pause >nul
