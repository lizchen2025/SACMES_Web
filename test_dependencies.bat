@echo off
REM Quick test script to verify dependencies can be installed
echo ============================================================
echo Testing Minimal Dependencies Installation
echo ============================================================
echo.

echo Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo.

echo Creating temporary test environment...
if exist test_env rmdir /s /q test_env
python -m venv test_env
call test_env\Scripts\activate.bat
echo.

echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo.

echo Testing dependencies installation...
pip install --no-cache-dir "python-socketio>=5.0.0,<6.0.0" "requests>=2.25.0"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    echo Trying with any available version...
    pip install --no-cache-dir python-socketio requests
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        deactivate
        rmdir /s /q test_env
        pause
        exit /b 1
    )
)
echo SUCCESS: Dependencies installed
echo.

echo Testing PyInstaller installation...
pip install --no-cache-dir pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller
    deactivate
    rmdir /s /q test_env
    pause
    exit /b 1
)
echo SUCCESS: PyInstaller installed
echo.

echo ============================================================
echo All dependencies can be installed successfully!
echo ============================================================
echo.
echo Cleaning up test environment...
deactivate
rmdir /s /q test_env
echo.
echo You can now run the build script:
echo   build_agent_minimal.bat
echo.
pause
