@echo off
setlocal enabledelayedexpansion

REM SACMES Agent - Portable Python Installer
REM This script installs embeddable Python 3.11.9 with pre-packaged tkinter

title SACMES Agent - Portable Python Installer

set PYTHON_VERSION=3.11.9
set PYTHON_EMBED_ZIP=python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_EMBED_ZIP%
set PYTHON_DIR=%~dp0sacmes_python
set TKINTER_SOURCE=%~dp0tkinter_package
set INSTALL_LOG=%~dp0install_log.txt

echo ========================================
echo SACMES Agent - Portable Python Setup
echo ========================================
echo.
echo This installer will set up a portable Python environment.
echo.
echo Components:
echo   - Python %PYTHON_VERSION% (embeddable)
echo   - tkinter GUI library (pre-packaged)
echo   - python-socketio
echo   - requests
echo.
echo Installation location: %PYTHON_DIR%
echo.
pause

echo. > "%INSTALL_LOG%"
echo Installation started: %date% %time% >> "%INSTALL_LOG%"

REM Check if tkinter_package exists
echo ========================================
echo Checking prerequisites
echo ========================================
echo.

if not exist "%TKINTER_SOURCE%" (
    echo [ERROR] tkinter_package folder not found
    echo Expected location: %TKINTER_SOURCE%
    echo.
    echo Please ensure you extracted all files from the distribution package.
    echo.
    pause
    exit /b 1
)

if not exist "%TKINTER_SOURCE%\Lib\tkinter" (
    echo [ERROR] tkinter files not found in tkinter_package
    echo.
    pause
    exit /b 1
)

echo [OK] Pre-packaged tkinter found

if not exist "%~dp0download_file.ps1" (
    echo [ERROR] download_file.ps1 not found
    echo.
    pause
    exit /b 1
)

echo [OK] Download script found

echo.
echo ========================================
echo Step 1/5: Download Python
echo ========================================
echo.

if not exist "%PYTHON_EMBED_ZIP%" (
    echo Downloading Python %PYTHON_VERSION% embeddable package...
    echo Size: Approximately 10 MB
    echo.

    powershell -ExecutionPolicy Bypass -File "%~dp0download_file.ps1" -Url "%PYTHON_EMBED_URL%" -OutFile "%PYTHON_EMBED_ZIP%"

    if not exist "%PYTHON_EMBED_ZIP%" (
        echo [ERROR] Download failed
        pause
        exit /b 1
    )
    echo [OK] Download complete
) else (
    echo [OK] Python package already downloaded
)

echo.
echo ========================================
echo Step 2/5: Extract Python
echo ========================================
echo.

if exist "%PYTHON_DIR%" (
    echo Removing old installation...
    rmdir /s /q "%PYTHON_DIR%"
)

mkdir "%PYTHON_DIR%"

powershell -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%PYTHON_EMBED_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

if not exist "%PYTHON_DIR%\python.exe" (
    echo [ERROR] Python extraction failed
    pause
    exit /b 1
)

echo [OK] Python extracted

echo.
echo ========================================
echo Step 3/5: Install tkinter
echo ========================================
echo.

echo Installing tkinter library...
xcopy "%TKINTER_SOURCE%\Lib\tkinter" "%PYTHON_DIR%\Lib\tkinter\" /E /I /Y >nul 2>&1

echo Installing tcl/tk runtime...
if exist "%TKINTER_SOURCE%\tcl" (
    xcopy "%TKINTER_SOURCE%\tcl" "%PYTHON_DIR%\tcl\" /E /I /Y >nul 2>&1
)

echo Installing DLL files...
if exist "%TKINTER_SOURCE%\DLLs\_tkinter.pyd" (
    copy "%TKINTER_SOURCE%\DLLs\*.pyd" "%PYTHON_DIR%\" >nul 2>&1
    copy "%TKINTER_SOURCE%\DLLs\*.dll" "%PYTHON_DIR%\" >nul 2>&1
)

echo [OK] tkinter installed

echo.
echo ========================================
echo Step 4/5: Configure Python
echo ========================================
echo.

if not exist "%PYTHON_DIR%\Lib" mkdir "%PYTHON_DIR%\Lib"

for %%f in ("%PYTHON_DIR%\python*._pth") do (
    echo python311.zip > "%%f"
    echo . >> "%%f"
    echo Lib >> "%%f"
    echo Lib\site-packages >> "%%f"
    echo. >> "%%f"
    echo import site >> "%%f"
)

echo [OK] Python configured

echo.
echo ========================================
echo Step 5/5: Install Python packages
echo ========================================
echo.

if not exist "%~dp0get-pip.py" (
    echo Downloading get-pip.py...
    powershell -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing"
)

echo Installing pip...
"%PYTHON_DIR%\python.exe" "%~dp0get-pip.py" --no-warn-script-location >nul 2>&1

echo Installing python-socketio and requests...
"%PYTHON_DIR%\python.exe" -m pip install python-socketio requests --quiet

if errorlevel 1 (
    echo [WARN] Package installation encountered issues, retrying...
    "%PYTHON_DIR%\python.exe" -m pip install python-socketio requests
)

echo [OK] Packages installed

echo.
echo ========================================
echo Verifying installation
echo ========================================
echo.

echo Python version:
"%PYTHON_DIR%\python.exe" --version

echo.
echo Testing packages...

REM Set environment variables for tkinter
set "TCL_LIBRARY=%PYTHON_DIR%\tcl\tcl8.6"
set "TK_LIBRARY=%PYTHON_DIR%\tcl\tk8.6"

"%PYTHON_DIR%\python.exe" -c "import tkinter; print('  [OK] tkinter')"
if errorlevel 1 (
    echo   [ERROR] tkinter failed to import
    echo.
    echo Troubleshooting:
    echo   - Verify tkinter_package folder was included in distribution
    echo   - Check that all DLL files are present
    echo.
    pause
    exit /b 1
)

"%PYTHON_DIR%\python.exe" -c "import socketio; print('  [OK] python-socketio')"
"%PYTHON_DIR%\python.exe" -c "import requests; print('  [OK] requests')"

echo.
echo ========================================
echo Installation Complete
echo ========================================
echo.
echo Python location: %PYTHON_DIR%
echo Python version: %PYTHON_VERSION%
echo GUI library: tkinter (pre-packaged)
echo.
echo Installation log: %INSTALL_LOG%
echo.

echo Installation completed: %date% %time% >> "%INSTALL_LOG%"

pause
