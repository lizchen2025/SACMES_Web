@echo off
setlocal enabledelayedexpansion

REM ========================================
REM SACMES Local - Python Environment Setup
REM ========================================

title SACMES Local - Python Setup

echo.
echo ============================================
echo   SACMES Local - Python Environment Setup
echo ============================================
echo.

:menu
echo Select Python configuration method:
echo.
echo   [1] Download Embedded Python (Recommended - Smallest)
echo       - Download Python 3.11 embedded (portable)
echo       - Extract to python_embedded folder
echo       - Auto-configure pip and install dependencies
echo       - Size: 15MB download + 60MB installed
echo.
echo   [2] Download Full Python Installer
echo       - Download Python 3.11 official installer
echo       - Install to python_local folder
echo       - Auto-install all dependencies
echo       - Size: 30MB download + 150MB installed
echo.
echo   [3] Use existing Python environment
echo       - Enter your Python.exe full path
echo       - Save config to python_path.txt
echo       - Auto-verify version and install deps
echo.
echo   [4] View manual installation guide
echo       - Show how to install system Python
echo       - Exit script for manual setup
echo.
echo   [0] Exit
echo.

set /p choice="Enter option [1/2/3/4/0]: "

if "%choice%"=="1" goto embedded_install
if "%choice%"=="2" goto auto_install
if "%choice%"=="3" goto custom_path
if "%choice%"=="4" goto manual_guide
if "%choice%"=="0" goto end
echo Invalid option, please try again
echo.
goto menu

REM ========================================
REM Option 1: Embedded Install
REM ========================================
:embedded_install
echo.
echo ============================================
echo   Option 1: Embedded Python (Portable)
echo ============================================
echo.
echo This will:
echo   1. Download Python 3.11.9 embedded (about 15MB)
echo   2. Extract to: %~dp0python_embedded\
echo   3. Auto-configure pip
echo   4. Install SACMES dependencies
echo.
echo Note: This may take 5-8 minutes. Keep network connected.
echo.

set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" goto menu

echo.
echo [1/5] Preparing to download Python embedded...
echo.

REM Set download URL for embedded Python
set PYTHON_VERSION=3.11.9
set EMBEDDED_FILE=python-%PYTHON_VERSION%-embed-amd64.zip
set DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%EMBEDDED_FILE%
set INSTALL_DIR=%~dp0python_embedded

REM Create temp directory
if not exist "%~dp0temp" mkdir "%~dp0temp"

echo Download URL: %DOWNLOAD_URL%
echo Save to: %~dp0temp\%EMBEDDED_FILE%
echo.

REM Download using PowerShell
echo Starting download... (this may take a few minutes)
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%~dp0temp\%EMBEDDED_FILE%'; if ($?) {Write-Host 'Download completed successfully'} else {Write-Host 'Download failed'; exit 1}}"

if errorlevel 1 (
    echo.
    echo [ERROR] Download failed!
    echo.
    echo Possible causes:
    echo   - Network connection issue
    echo   - Firewall blocking
    echo   - Python website temporarily unavailable
    echo.
    echo Please try another installation method or retry later.
    pause
    goto menu
)

echo.
echo [2/5] Extracting Python to python_embedded folder...
echo.

REM Extract using PowerShell
if exist "%INSTALL_DIR%" (
    echo Removing old installation...
    rmdir /s /q "%INSTALL_DIR%"
)

powershell -Command "Expand-Archive -Path '%~dp0temp\%EMBEDDED_FILE%' -DestinationPath '%INSTALL_DIR%' -Force"

if not exist "%INSTALL_DIR%\python.exe" (
    echo [ERROR] Extraction failed!
    pause
    goto menu
)

echo [OK] Python extracted successfully!
echo.

echo [3/5] Configuring pip support...
echo.

REM Find the _pth file and modify it to enable site-packages
for %%f in ("%INSTALL_DIR%\python*._pth") do (
    echo Modifying %%f to enable site-packages...

    REM Create new _pth file with site-packages enabled
    (
        echo python311.zip
        echo .
        echo.
        echo # Uncomment to enable site-packages
        echo import site
    ) > "%%f.new"

    move /y "%%f.new" "%%f" >nul
)

echo.
echo [4/5] Installing pip...
echo.

REM Download get-pip.py
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%~dp0temp\get-pip.py'"

if errorlevel 1 (
    echo [ERROR] Failed to download get-pip.py
    pause
    goto menu
)

REM Install pip
"%INSTALL_DIR%\python.exe" "%~dp0temp\get-pip.py" --quiet --disable-pip-version-check

if errorlevel 1 (
    echo [ERROR] Failed to install pip
    pause
    goto menu
)

echo [OK] pip installed successfully!
echo.

REM Save Python path to config file
echo %INSTALL_DIR%\python.exe > "%~dp0python_path.txt"

echo [5/5] Installing SACMES dependencies...
echo This may take 3-5 minutes...
echo.

"%INSTALL_DIR%\python.exe" -m pip install -r "%~dp0requirements_local.txt" --quiet --disable-pip-version-check

if errorlevel 1 (
    echo.
    echo [WARNING] Some dependencies failed to install
    echo Will retry during startup
    echo.
) else (
    echo [OK] All dependencies installed successfully!
)

echo.
echo Cleaning up temporary files...
del "%~dp0temp\%EMBEDDED_FILE%" >nul 2>&1
del "%~dp0temp\get-pip.py" >nul 2>&1
rmdir "%~dp0temp" >nul 2>&1

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Python path saved to: python_path.txt
echo Install location: %INSTALL_DIR%
echo Total size: Approximately 60-80MB
echo.
echo You can now run start.bat to launch the application!
echo.
pause
goto end

REM ========================================
REM Option 2: Full Python Install
REM ========================================
:auto_install
echo.
echo ============================================
echo   Option 2: Full Python Installer
echo ============================================
echo.
echo This will:
echo   1. Download Python 3.11.9 installer (about 30MB)
echo   2. Install to: %~dp0python_local\
echo   3. Auto-install SACMES dependencies
echo.
echo Note: This may take 5-10 minutes. Keep network connected.
echo.

set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" goto menu

echo.
echo [1/4] Preparing to download Python installer...
echo.

REM Set download URL and filename
set PYTHON_VERSION=3.11.9
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%
set INSTALL_DIR=%~dp0python_local

REM Create temp directory
if not exist "%~dp0temp" mkdir "%~dp0temp"

echo Download URL: %DOWNLOAD_URL%
echo Save to: %~dp0temp\%PYTHON_INSTALLER%
echo.

REM Download using PowerShell (more reliable than bitsadmin)
echo Starting download... (this may take a few minutes)
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%~dp0temp\%PYTHON_INSTALLER%'; if ($?) {Write-Host 'Download completed successfully'} else {Write-Host 'Download failed'; exit 1}}"

if errorlevel 1 (
    echo.
    echo [ERROR] Download failed!
    echo.
    echo Possible causes:
    echo   - Network connection issue
    echo   - Firewall blocking
    echo   - Python website temporarily unavailable
    echo.
    echo Please try another installation method or retry later.
    pause
    goto menu
)

echo.
echo [2/4] Installing Python to local directory...
echo.
echo Install location: %INSTALL_DIR%
echo This may take 2-3 minutes, please wait...
echo.

REM Silent install Python
"%~dp0temp\%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_tcltk=0 TargetDir="%INSTALL_DIR%"

REM Wait for installation to complete
timeout /t 5 /nobreak >nul

REM Verify installation
if not exist "%INSTALL_DIR%\python.exe" (
    echo.
    echo [ERROR] Python installation failed!
    echo.
    echo Please check:
    echo   1. Sufficient disk space (need about 150MB)
    echo   2. Administrator permissions
    echo   3. Antivirus software not blocking
    pause
    goto menu
)

echo [OK] Python installed successfully!
echo.

REM Save Python path to config file
echo %INSTALL_DIR%\python.exe > "%~dp0python_path.txt"

echo [3/4] Upgrading pip...
"%INSTALL_DIR%\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check

echo.
echo [4/4] Installing SACMES dependencies...
echo This may take 3-5 minutes...
echo.

"%INSTALL_DIR%\python.exe" -m pip install -r "%~dp0requirements_local.txt" --quiet --disable-pip-version-check

if errorlevel 1 (
    echo.
    echo [WARNING] Some dependencies failed to install
    echo Will retry during startup
    echo.
) else (
    echo [OK] All dependencies installed successfully!
)

echo.
echo Cleaning up temporary files...
del "%~dp0temp\%PYTHON_INSTALLER%" >nul 2>&1
rmdir "%~dp0temp" >nul 2>&1

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Python path saved to: python_path.txt
echo Install location: %INSTALL_DIR%
echo.
echo You can now run start.bat to launch the application!
echo.
pause
goto end

REM ========================================
REM Option 3: Custom Path
REM ========================================
:custom_path
echo.
echo ============================================
echo   Option 3: Use Existing Python Environment
echo ============================================
echo.
echo Enter the full path to your Python.exe
echo.
echo Examples:
echo   C:\Python311\python.exe
echo   D:\Anaconda3\python.exe
echo   C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe
echo.

set /p CUSTOM_PYTHON="Python path: "

REM Remove quotes
set CUSTOM_PYTHON=%CUSTOM_PYTHON:"=%

REM Verify path
if not exist "%CUSTOM_PYTHON%" (
    echo.
    echo [ERROR] File not found: %CUSTOM_PYTHON%
    echo.
    echo Please check the path and try again.
    pause
    goto menu
)

echo.
echo Verifying Python version...
"%CUSTOM_PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This is not a valid Python executable
    pause
    goto menu
)

REM Get version
for /f "tokens=2" %%i in ('"%CUSTOM_PYTHON%" --version 2^>^&1') do set PY_VERSION=%%i
echo [OK] Detected version: %PY_VERSION%

REM Validate version >= 3.9
for /f "tokens=1,2 delims=." %%a in ("%PY_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo [ERROR] Python version too low, need 3.9 or higher
    pause
    goto menu
)

if %MAJOR% EQU 3 if %MINOR% LSS 9 (
    echo [ERROR] Python version too low, need 3.9 or higher
    pause
    goto menu
)

echo.
echo Saving config to python_path.txt...
echo %CUSTOM_PYTHON% > "%~dp0python_path.txt"
echo [OK] Config saved

echo.
set /p install_deps="Install SACMES dependencies now? (y/n): "
if /i "%install_deps%"=="y" (
    echo.
    echo Installing dependencies...
    "%CUSTOM_PYTHON%" -m pip install -r "%~dp0requirements_local.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo [WARNING] Some dependencies failed to install, will retry on startup
    ) else (
        echo [OK] Dependencies installed successfully
    )
)

echo.
echo ============================================
echo   Configuration Complete!
echo ============================================
echo.
echo Python path: %CUSTOM_PYTHON%
echo Config file: python_path.txt
echo.
echo You can now run start.bat to launch the application!
echo.
pause
goto end

REM ========================================
REM Option 4: Manual Guide
REM ========================================
:manual_guide
echo.
echo ============================================
echo   Option 4: Manual Python Installation Guide
echo ============================================
echo.
echo Step 1: Download Python
echo   Visit: https://www.python.org/downloads/
echo   Download: Python 3.9 or higher for Windows
echo.
echo Step 2: Install Python
echo   IMPORTANT: Check "Add Python to PATH" during installation
echo   - Double-click the downloaded installer
echo   - On the first screen, CHECK "Add Python to PATH"
echo   - Click "Install Now"
echo   - Wait for installation to complete
echo.
echo Step 3: Verify Installation
echo   - Open a new Command Prompt window
echo   - Type: python --version
echo   - Should display: Python 3.x.x
echo.
echo Step 4: Run SACMES
echo   - Close this window
echo   - Double-click start.bat
echo   - Should auto-detect Python and start
echo.
echo ============================================
echo.
pause
goto end

:end
echo.
echo Thank you for using SACMES Local!
echo.
exit /b 0
