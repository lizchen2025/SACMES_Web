@echo off
REM SACMES Agent - First Time Setup
REM This script downloads a portable Python environment and installs required packages

setlocal enabledelayedexpansion

echo ========================================
echo SACMES Agent - First Time Setup
echo ========================================
echo.
echo This will download and set up Python (approx. 25 MB)
echo and install required packages (approx. 5 MB)
echo.
echo Total download: ~30 MB
echo This only needs to be done once.
echo.
pause

REM Configuration
set PYTHON_VERSION=3.11.9
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_DIR=python_embed
set PYTHON_ZIP=python_embed.zip

echo [1/4] Downloading Python %PYTHON_VERSION% embeddable...
echo.

REM Download Python using PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'}"

if not exist "%PYTHON_ZIP%" (
    echo ERROR: Failed to download Python
    exit /b 1
)

echo [2/4] Extracting Python...
echo.

REM Extract using PowerShell
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

if not exist "%PYTHON_DIR%\python.exe" (
    echo ERROR: Failed to extract Python
    exit /b 1
)

REM Clean up zip file
del "%PYTHON_ZIP%"

echo [3/4] Configuring Python...
echo.

REM Enable pip by uncommenting import site in python*._pth file
for %%f in (%PYTHON_DIR%\python*._pth) do (
    powershell -Command "(Get-Content '%%f') -replace '#import site', 'import site' | Set-Content '%%f'"
)

REM Download and install pip
echo Downloading pip installer...
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"
%PYTHON_DIR%\python.exe %PYTHON_DIR%\get-pip.py --no-warn-script-location
del %PYTHON_DIR%\get-pip.py

echo [4/4] Installing required packages...
echo.

REM Install required packages
%PYTHON_DIR%\python.exe -m pip install --no-warn-script-location python-socketio requests --quiet

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Python and all dependencies have been installed.
echo You can now run start_agent.bat to launch the agent.
echo.
pause
