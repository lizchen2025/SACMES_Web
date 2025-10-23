@echo off
REM SACMES Agent - Full Python Installer with Registry Cleanup v4.0
REM This version cleans registry before installing to avoid conflicts

setlocal enabledelayedexpansion

REM Get script directory and change to it
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo SACMES Agent - Setup v4.0
echo ========================================
echo.
echo Full Python with tkinter (GUI support)
echo ========================================
echo.
echo Script directory: %SCRIPT_DIR%
echo Working directory: %CD%
echo.

REM Configuration
set PYTHON_VERSION=3.11.9
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%
set PYTHON_DIR=%CD%\sacmes_python
set INSTALL_LOG=%CD%\install_log.txt

REM Generate unique installation ID to avoid registry conflicts
set UNIQUE_ID=%RANDOM%-%RANDOM%

REM Clear previous log
if exist "%INSTALL_LOG%" del "%INSTALL_LOG%"

echo ===== SACMES Agent Installation Log ===== > "%INSTALL_LOG%"
echo Time: %date% %time% >> "%INSTALL_LOG%"
echo Script Directory: %SCRIPT_DIR% >> "%INSTALL_LOG%"
echo Working Directory: %CD% >> "%INSTALL_LOG%"
echo Target Directory: %PYTHON_DIR% >> "%INSTALL_LOG%"
echo Unique ID: %UNIQUE_ID% >> "%INSTALL_LOG%"
echo ========================================== >> "%INSTALL_LOG%"
echo. >> "%INSTALL_LOG%"

echo Log file created: %INSTALL_LOG%
echo.

REM ========================================
REM STEP 1: Check Existing Installation
REM ========================================
echo [STEP 1] Checking for existing installation...
echo [STEP 1] Checking existing installation >> "%INSTALL_LOG%"

if exist "%PYTHON_DIR%" (
    echo Found existing installation, testing...
    echo Existing installation found >> "%INSTALL_LOG%"

    if exist "%PYTHON_DIR%\python.exe" (
        "%PYTHON_DIR%\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            echo Python is working, checking packages...
            "%PYTHON_DIR%\python.exe" -m pip show python-socketio >nul 2>&1
            if not errorlevel 1 (
                "%PYTHON_DIR%\python.exe" -c "import tkinter" >nul 2>&1
                if not errorlevel 1 (
                    echo.
                    echo ========================================
                    echo Already Installed!
                    echo ========================================
                    echo.
                    echo Python with tkinter is already installed.
                    echo All packages are installed.
                    echo.
                    echo You can run start_agent.bat now.
                    echo.
                    pause
                    exit /b 0
                ) else (
                    echo Python OK, but tkinter missing >> "%INSTALL_LOG%"
                    echo Python works but tkinter is missing.
                    echo Will reinstall with tkinter support.
                    goto :CLEANUP_OLD
                )
            ) else (
                echo Python OK, but packages missing >> "%INSTALL_LOG%"
                echo Python works but packages are missing.
                goto :INSTALL_PACKAGES
            )
        )
    )

    :CLEANUP_OLD
    echo Existing installation is incomplete.
    echo Removing old installation...
    echo Removing old installation >> "%INSTALL_LOG%"

    rmdir /s /q "%PYTHON_DIR%" 2>>"%INSTALL_LOG%"
    timeout /t 2 /nobreak >nul

    if exist "%PYTHON_DIR%" (
        echo WARNING: Could not fully remove old installation
        echo Some files may be locked. Will try to continue...
        echo Partial removal >> "%INSTALL_LOG%"
    )
)

echo No complete installation found.
echo.

REM ========================================
REM STEP 2: Clean Registry (KEY STEP!)
REM ========================================
echo ========================================
echo [STEP 2] Cleaning Previous Registry Entries
echo ========================================
echo.
echo This prevents "Modify/Repair/Uninstall" dialog...
echo [STEP 2] Cleaning registry >> "%INSTALL_LOG%"

REM Clean up any previous Python registry entries for this location
REM This is the KEY to avoiding the Modify/Repair dialog!

echo Searching for conflicting registry entries...

powershell -ExecutionPolicy Bypass -Command "& { $ErrorActionPreference='SilentlyContinue'; Write-Host 'Scanning registry locations...'; $regPaths = @('HKCU:\Software\Python\PythonCore\3.11', 'HKLM:\Software\Python\PythonCore\3.11', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'); $found = $false; $scanned = 0; foreach($path in $regPaths) { $scanned++; if(Test-Path $path) { $items = @(Get-ChildItem $path -ErrorAction SilentlyContinue); foreach($item in $items) { $props = Get-ItemProperty $item.PSPath -ErrorAction SilentlyContinue; if($props.InstallLocation -like '*sacmes_python*' -or $props.InstallLocation -like '*python_embed*') { Write-Host 'FOUND CONFLICT:'; Write-Host \"  Registry: $($item.PSPath)\"; Write-Host \"  Location: $($props.InstallLocation)\"; try { Remove-Item $item.PSPath -Recurse -Force -ErrorAction Stop; Write-Host '  STATUS: Removed successfully'; $found = $true; } catch { Write-Host \"  STATUS: Could not remove - $($_.Exception.Message)\"; Write-Host '  TIP: Try running as Administrator'; } } } } } if($found) { Write-Host 'Registry cleanup complete!'; Write-Host 'Old installation records removed.'; } else { Write-Host 'No conflicts found - clean start!'; } Write-Host \"Scanned $scanned registry locations.\"; }" 2>>"%INSTALL_LOG%"

echo.
echo Registry check complete.
echo.

echo This will download and install Python (~30 MB)
echo with full tkinter GUI support.
echo.
echo Total download: ~30 MB
echo This only needs to be done once.
echo.
pause

REM ========================================
REM STEP 3: Download Python Installer
REM ========================================
echo.
echo ========================================
echo [STEP 3] Downloading Python %PYTHON_VERSION%
echo ========================================
echo.

echo Downloading full installer with tkinter...
echo Please wait, this may take 2-3 minutes...
echo.
echo Download URL: %PYTHON_URL% >> "%INSTALL_LOG%"

powershell -Command "& { $ProgressPreference = 'SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Write-Host 'Connecting to python.org...'; $wc = New-Object System.Net.WebClient; $wc.DownloadFile('%PYTHON_URL%', '%PYTHON_INSTALLER%'); Write-Host 'Download complete!'; exit 0 } catch { Write-Host ''; Write-Host 'ERROR downloading Python:'; Write-Host $_.Exception.Message; Write-Host ''; exit 1 }}" 2>>"%INSTALL_LOG%"

if errorlevel 1 (
    echo Download failed >> "%INSTALL_LOG%"
    goto :DOWNLOAD_FAILED
)

if not exist "%PYTHON_INSTALLER%" (
    echo ERROR: Download failed - file not created >> "%INSTALL_LOG%"
    goto :DOWNLOAD_FAILED
)

echo Download successful!
echo Download OK >> "%INSTALL_LOG%"

REM ========================================
REM STEP 4: Install Python with Unique ID
REM ========================================
echo.
echo ========================================
echo [STEP 4] Installing Python
echo ========================================
echo.

echo Installing Python (this may take 2-3 minutes)...
echo Please wait...
echo.
echo [STEP 4] Installing >> "%INSTALL_LOG%"

REM Use unique TargetDir name to avoid registry detection
REM But create symlink to standard name after install
set TEMP_INSTALL_DIR=%PYTHON_DIR%_%UNIQUE_ID%

echo Installing to temporary location: %TEMP_INSTALL_DIR% >> "%INSTALL_LOG%"
echo Final location will be: %PYTHON_DIR% >> "%INSTALL_LOG%"

REM Install with unique directory name
"%PYTHON_INSTALLER%" /quiet /log "%INSTALL_LOG%" InstallAllUsers=0 TargetDir="%TEMP_INSTALL_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0 CompileAll=0

echo Waiting for installation to complete...
timeout /t 10 /nobreak >nul

REM Check if installation succeeded
if not exist "%TEMP_INSTALL_DIR%\python.exe" (
    echo ERROR: Installation failed >> "%INSTALL_LOG%"
    echo Installation failed - python.exe not found
    del "%PYTHON_INSTALLER%" 2>nul
    goto :INSTALLATION_FAILED
)

echo Installation successful!
echo Installation OK >> "%INSTALL_LOG%"

REM Move from temp directory to final directory
if exist "%PYTHON_DIR%" (
    echo Removing old target directory...
    rmdir /s /q "%PYTHON_DIR%" 2>nul
)

echo Moving to final location...
move "%TEMP_INSTALL_DIR%" "%PYTHON_DIR%" >nul 2>>"%INSTALL_LOG%"

if not exist "%PYTHON_DIR%\python.exe" (
    echo ERROR: Could not move to final location >> "%INSTALL_LOG%"
    if exist "%TEMP_INSTALL_DIR%\python.exe" (
        echo Installation is at: %TEMP_INSTALL_DIR%
        echo You can manually rename this folder to: %PYTHON_DIR%
    )
    goto :INSTALLATION_FAILED
)

REM Clean up installer
del "%PYTHON_INSTALLER%" 2>nul

REM Test Python and tkinter
echo.
echo Testing Python installation...
"%PYTHON_DIR%\python.exe" --version
if errorlevel 1 (
    echo ERROR: Python is not working >> "%INSTALL_LOG%"
    goto :INSTALLATION_FAILED
)

echo Testing tkinter...
"%PYTHON_DIR%\python.exe" -c "import tkinter; print('tkinter OK')"
if errorlevel 1 (
    echo WARNING: tkinter not available
    echo tkinter test failed >> "%INSTALL_LOG%"
) else (
    echo tkinter is working!
    echo tkinter OK >> "%INSTALL_LOG%"
)

REM ========================================
REM STEP 5: Install Packages
REM ========================================
:INSTALL_PACKAGES
echo.
echo ========================================
echo [STEP 5] Installing Required Packages
echo ========================================
echo.

echo Checking pip...
"%PYTHON_DIR%\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo Pip not available >> "%INSTALL_LOG%"
    goto :INSTALLATION_FAILED
)

echo Pip is working!
echo.

echo Upgrading pip...
echo Upgrading pip >> "%INSTALL_LOG%"
"%PYTHON_DIR%\python.exe" -m pip install --upgrade pip --quiet >>"%INSTALL_LOG%" 2>&1

echo Installing python-socketio and requests...
echo This may take 30-60 seconds...
echo Installing packages >> "%INSTALL_LOG%"

"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location python-socketio requests >>"%INSTALL_LOG%" 2>&1

if errorlevel 1 (
    echo.
    echo WARNING: Package installation had issues
    echo Retrying with verbose output...
    echo.
    "%PYTHON_DIR%\python.exe" -m pip install python-socketio requests

    if errorlevel 1 (
        echo Package installation failed >> "%INSTALL_LOG%"
        goto :PACKAGE_FAILED
    )
)

echo.
echo Verifying packages...
"%PYTHON_DIR%\python.exe" -c "import socketio; import requests; import tkinter; print('All imports OK')" 2>>"%INSTALL_LOG%"
if errorlevel 1 (
    echo Package verification failed >> "%INSTALL_LOG%"
    goto :PACKAGE_FAILED
)

REM ========================================
REM Installation Complete!
REM ========================================
echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.

echo Installation completed successfully! >> "%INSTALL_LOG%"

echo Python location: %PYTHON_DIR%
echo.

echo Installed version:
"%PYTHON_DIR%\python.exe" --version
echo.

echo Installed packages:
"%PYTHON_DIR%\python.exe" -m pip list | findstr /i "socketio requests"
echo.

echo ========================================
echo Ready to Use!
echo ========================================
echo.
echo Python with full tkinter GUI support is installed!
echo You can now run start_agent.bat to start the agent.
echo.

REM Mark installation as complete
echo SUCCESS > "%PYTHON_DIR%\.install_complete"
echo %date% %time% >> "%PYTHON_DIR%\.install_complete"

pause
exit /b 0

REM ========================================
REM Error Handlers
REM ========================================

:DOWNLOAD_FAILED
echo.
echo ========================================
echo ERROR: Download Failed
echo ========================================
echo.
echo Could not download Python from python.org
echo.
echo Possible causes:
echo 1. No internet connection
echo 2. Firewall blocking python.org
echo 3. Antivirus blocking the download
echo.
echo SOLUTIONS:
echo.
echo [Option 1] Check your internet and try again
echo   - Make sure you can access python.org in browser
echo   - Temporarily disable antivirus/firewall
echo   - Try again
echo.
echo [Option 2] Manual download
echo   1. Open browser and download:
echo      %PYTHON_URL%
echo   2. Save as: %PYTHON_INSTALLER%
echo   3. Place the file in this folder: %CD%
echo   4. Run this installer again
echo.
echo Check install_log.txt for technical details.
echo.
pause
exit /b 1

:PACKAGE_FAILED
echo.
echo ========================================
echo ERROR: Package Installation Failed
echo ========================================
echo.
echo Python is installed but could not install packages
echo.
echo You can try to install packages manually:
echo.
echo   %PYTHON_DIR%\python.exe -m pip install python-socketio requests
echo.
echo Or check install_log.txt for details.
echo.
pause
exit /b 1

:INSTALLATION_FAILED
echo.
echo ========================================
echo ERROR: Installation Failed
echo ========================================
echo.
echo Automatic installation could not complete.
echo.
echo Please check install_log.txt for detailed error information.
echo.
echo TROUBLESHOOTING:
echo.
echo If you see "Modify/Repair/Uninstall" dialog again:
echo.
echo 1. Close the dialog (click X)
echo 2. Delete these folders:
echo    - %PYTHON_DIR%
echo    - Any folder starting with sacmes_python_
echo 3. Restart your computer (clears locked registry)
echo 4. Run this installer again
echo.
echo Alternatively, run as Administrator to force registry cleanup.
echo.
pause
exit /b 1
