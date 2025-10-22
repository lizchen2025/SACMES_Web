@echo off
REM SACMES Agent - First Time Setup (Robust Version)
REM This script provides multiple fallback methods for Python installation

setlocal enabledelayedexpansion

echo ========================================
echo SACMES Agent - First Time Setup
echo ========================================
echo.

REM Configuration
set PYTHON_VERSION=3.11.9
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_DIR=%CD%\python_embed
set INSTALL_LOG=%CD%\install_log.txt

REM Clear previous log
if exist "%INSTALL_LOG%" del "%INSTALL_LOG%"

echo [Check] Looking for existing Python installation...
echo.

REM Check if Python is already installed
if exist "%PYTHON_DIR%\python.exe" (
    echo Found existing Python installation at: %PYTHON_DIR%
    echo Testing if it works...

    "%PYTHON_DIR%\python.exe" --version >nul 2>&1
    if not errorlevel 1 (
        echo Existing Python installation is working!
        echo.
        goto :VERIFY_PACKAGES
    ) else (
        echo WARNING: Existing installation appears corrupted.
        echo Removing and reinstalling...
        rmdir /s /q "%PYTHON_DIR%" 2>nul
    )
)

echo No existing installation found.
echo.
echo This will download and set up Python (approx. 30 MB)
echo and install required packages (approx. 5 MB)
echo.
echo Total download: ~35 MB
echo This only needs to be done once.
echo.
pause

REM ========================================
REM Method 1: Try full Python installer
REM ========================================
echo.
echo ========================================
echo METHOD 1: Full Python Installer
echo ========================================
echo.
echo [1/4] Downloading Python %PYTHON_VERSION% installer...
echo.

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -TimeoutSec 120; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }}" 2>>"%INSTALL_LOG%"

if not exist "%PYTHON_INSTALLER%" (
    echo WARNING: Failed to download full installer
    echo See install_log.txt for details
    goto :TRY_EMBEDDABLE
)

echo [2/4] Installing Python to local directory...
echo.
echo This may take 1-2 minutes, please wait...
echo.

REM Clear any PATH conflicts temporarily
set "OLD_PATH=%PATH%"
set "PATH=%SystemRoot%\system32;%SystemRoot%"

REM Try silent installation
"%PYTHON_INSTALLER%" /quiet /log "%INSTALL_LOG%" InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0 CompileAll=0

REM Wait for installation
echo Waiting for installation to complete...
timeout /t 5 /nobreak >nul

REM Restore PATH
set "PATH=%OLD_PATH%"

REM Verify installation
if exist "%PYTHON_DIR%\python.exe" (
    echo [3/4] Verifying installation...
    "%PYTHON_DIR%\python.exe" --version >>"%INSTALL_LOG%" 2>&1
    if not errorlevel 1 (
        echo SUCCESS: Python installed successfully
        del "%PYTHON_INSTALLER%" 2>nul
        goto :VERIFY_TKINTER
    )
)

echo WARNING: Silent installation did not complete successfully
echo.
echo Trying alternative installation with UI...
"%PYTHON_INSTALLER%" InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0
timeout /t 5 /nobreak >nul

if exist "%PYTHON_DIR%\python.exe" (
    del "%PYTHON_INSTALLER%" 2>nul
    goto :VERIFY_TKINTER
)

echo Installation method 1 failed.
del "%PYTHON_INSTALLER%" 2>nul

REM ========================================
REM Method 2: Try embeddable Python
REM ========================================
:TRY_EMBEDDABLE
echo.
echo ========================================
echo METHOD 2: Embeddable Python (Fallback)
echo ========================================
echo.
echo Trying embeddable Python package...
echo This is more reliable but requires manual pip installation.
echo.

set PYTHON_ZIP=python-%PYTHON_VERSION%-embed-amd64.zip

echo Downloading embeddable Python...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%PYTHON_EMBED_URL%' -OutFile '%PYTHON_ZIP%' -TimeoutSec 120; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }}" 2>>"%INSTALL_LOG%"

if not exist "%PYTHON_ZIP%" (
    echo ERROR: Failed to download embeddable Python
    goto :INSTALLATION_FAILED
)

echo Extracting Python...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force" 2>>"%INSTALL_LOG%"
del "%PYTHON_ZIP%" 2>nul

if not exist "%PYTHON_DIR%\python.exe" (
    echo ERROR: Extraction failed
    goto :INSTALLATION_FAILED
)

echo Configuring embeddable Python for pip...
REM Enable site-packages by uncommenting import site
powershell -Command "(Get-Content '%PYTHON_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python311._pth'" 2>>"%INSTALL_LOG%"

echo Installing pip...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'}" 2>>"%INSTALL_LOG%"
if exist "get-pip.py" (
    "%PYTHON_DIR%\python.exe" get-pip.py >>"%INSTALL_LOG%" 2>&1
    del get-pip.py 2>nul
)

echo SUCCESS: Embeddable Python installed
echo.
echo NOTE: tkinter is not available in embeddable Python.
echo The agent will work but GUI features will be limited.
echo.

goto :INSTALL_PACKAGES

REM ========================================
REM Verify tkinter (only for full install)
REM ========================================
:VERIFY_TKINTER
echo [3/4] Verifying tkinter installation...
echo.

"%PYTHON_DIR%\python.exe" -c "import tkinter; print('tkinter OK')" >nul 2>&1
if errorlevel 1 (
    echo WARNING: tkinter is not available
    echo The agent may have limited GUI functionality
) else (
    echo SUCCESS: tkinter is working
)
echo.

REM ========================================
REM Install required packages
REM ========================================
:VERIFY_PACKAGES
echo Checking existing packages...
"%PYTHON_DIR%\python.exe" -m pip show python-socketio >nul 2>&1
if not errorlevel 1 (
    echo Packages already installed! Skipping installation.
    goto :COMPLETE
)

:INSTALL_PACKAGES
echo [4/4] Installing required packages...
echo.

REM Ensure pip is up to date
echo Updating pip...
"%PYTHON_DIR%\python.exe" -m pip install --upgrade pip >>"%INSTALL_LOG%" 2>&1

echo Installing python-socketio and requests...
"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location python-socketio requests >>"%INSTALL_LOG%" 2>&1

if errorlevel 1 (
    echo WARNING: Package installation encountered issues
    echo Retrying with verbose output...
    "%PYTHON_DIR%\python.exe" -m pip install python-socketio requests
    if errorlevel 1 (
        echo ERROR: Failed to install required packages
        echo Please check install_log.txt for details
        pause
        exit /b 1
    )
)

echo SUCCESS: All packages installed
echo.

REM ========================================
REM Completion
REM ========================================
:COMPLETE
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Python installation location: %PYTHON_DIR%
echo.

REM Show Python version
echo Installed version:
"%PYTHON_DIR%\python.exe" --version
echo.

echo Required packages:
"%PYTHON_DIR%\python.exe" -m pip list | findstr /i "socketio requests"
echo.

echo You can now run start_agent.bat to launch the agent.
echo.
pause
exit /b 0

REM ========================================
REM Installation failed handler
REM ========================================
:INSTALLATION_FAILED
echo.
echo ========================================
echo Installation Failed
echo ========================================
echo.
echo Automatic installation could not complete.
echo.
echo MANUAL INSTALLATION OPTION:
echo.
echo 1. Download Python 3.11.9 from: https://www.python.org/downloads/
echo 2. Install it to: %PYTHON_DIR%
echo 3. Make sure to check "Add to PATH" during installation
echo 4. Run this script again
echo.
echo Alternatively, check install_log.txt for detailed error information.
echo.
pause
exit /b 1
