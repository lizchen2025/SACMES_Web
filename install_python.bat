@echo off
REM SACMES Agent - First Time Setup
REM This script downloads a full Python environment with tkinter and installs required packages

setlocal enabledelayedexpansion

echo ========================================
echo SACMES Agent - First Time Setup
echo ========================================
echo.
echo This will download and set up Python (approx. 30 MB)
echo and install required packages (approx. 5 MB)
echo.
echo Total download: ~35 MB
echo This only needs to be done once.
echo.
pause

REM Configuration
set PYTHON_VERSION=3.11.9
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%
set PYTHON_DIR=%CD%\python_embed

echo [1/4] Downloading Python %PYTHON_VERSION% installer...
echo.

REM Download Python installer using PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'}"

if not exist "%PYTHON_INSTALLER%" (
    echo ERROR: Failed to download Python installer
    exit /b 1
)

echo [2/4] Installing Python (this may take a minute)...
echo.

REM Install Python silently to local directory
REM InstallAllUsers=0 - Install for current user only
REM TargetDir - Install to local directory
REM Include_pip=1 - Include pip
REM Include_tcltk=1 - Include tkinter (IMPORTANT!)
REM PrependPath=0 - Don't modify system PATH
REM Shortcuts=0 - Don't create shortcuts
REM /quiet - Silent installation
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0

REM Wait for installation to complete
timeout /t 3 /nobreak >nul

if not exist "%PYTHON_DIR%\python.exe" (
    echo ERROR: Python installation failed
    echo Trying alternative installation method...

    REM Try without quiet mode for debugging
    "%PYTHON_INSTALLER%" InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0

    if not exist "%PYTHON_DIR%\python.exe" (
        echo ERROR: Installation failed. Please check error messages above.
        pause
        exit /b 1
    )
)

REM Clean up installer
del "%PYTHON_INSTALLER%"

echo [3/4] Verifying tkinter installation...
echo.

REM Test if tkinter is available
"%PYTHON_DIR%\python.exe" -c "import tkinter; print('tkinter OK')" >nul 2>&1
if errorlevel 1 (
    echo WARNING: tkinter may not be installed correctly
    echo The agent may not start properly
) else (
    echo tkinter is installed and working
)

echo [4/4] Installing required packages...
echo.

REM Install required packages
"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location python-socketio requests --quiet

if errorlevel 1 (
    echo ERROR: Failed to install packages
    echo Retrying with verbose output...
    "%PYTHON_DIR%\python.exe" -m pip install python-socketio requests
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Python and all dependencies have been installed.
echo You can now run start_agent.bat to launch the agent.
echo.
pause
