@echo off
REM SACMES Agent - Ultra-Robust Installation v3.0
REM Handles registry conflicts and provides detailed diagnostics

setlocal enabledelayedexpansion

echo ========================================
echo SACMES Agent - First Time Setup v3.0
echo ========================================
echo.

REM Configuration
set PYTHON_VERSION=3.11.9
set PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set PYTHON_DIR=%CD%\python_embed
set INSTALL_LOG=%CD%\install_log.txt
set VERBOSE_LOG=%CD%\install_verbose.log

REM Clear previous logs
if exist "%INSTALL_LOG%" del "%INSTALL_LOG%"
if exist "%VERBOSE_LOG%" del "%VERBOSE_LOG%"

echo [Diagnostic] Starting installation diagnostics... >> "%VERBOSE_LOG%"
echo Time: %date% %time% >> "%VERBOSE_LOG%"
echo Working Directory: %CD% >> "%VERBOSE_LOG%"
echo Target Directory: %PYTHON_DIR% >> "%VERBOSE_LOG%"
echo. >> "%VERBOSE_LOG%"

echo ========================================
echo STEP 1: System Check
echo ========================================
echo.

REM Check for existing Python installation
if exist "%PYTHON_DIR%" (
    echo [Check] Found existing python_embed directory
    echo [Check] Existing python_embed directory found >> "%VERBOSE_LOG%"

    if exist "%PYTHON_DIR%\python.exe" (
        echo [Test] Testing existing Python...
        echo [Test] Testing existing python.exe >> "%VERBOSE_LOG%"

        "%PYTHON_DIR%\python.exe" --version >nul 2>&1
        if not errorlevel 1 (
            echo [OK] Existing Python installation works!
            echo [OK] Existing Python works, checking packages... >> "%VERBOSE_LOG%"

            REM Check if packages are installed
            "%PYTHON_DIR%\python.exe" -m pip show python-socketio >nul 2>&1
            if not errorlevel 1 (
                echo [OK] All packages already installed!
                echo.
                echo Installation is complete and working.
                echo You can run start_agent.bat now.
                echo.
                pause
                exit /b 0
            ) else (
                echo [Info] Python works but packages missing
                echo [Info] Python OK, packages missing >> "%VERBOSE_LOG%"
                goto :INSTALL_PACKAGES
            )
        ) else (
            echo [Warning] Existing Python installation is corrupted
            echo [Warning] Corrupted Python detected >> "%VERBOSE_LOG%"
        )
    )

    REM If we get here, installation is incomplete or corrupted
    echo.
    echo [Action] Removing incomplete installation...
    echo [Action] Removing corrupted installation >> "%VERBOSE_LOG%"

    REM Try to remove, but don't fail if it doesn't work
    rmdir /s /q "%PYTHON_DIR%" 2>>"%VERBOSE_LOG%"
    timeout /t 2 /nobreak >nul

    if exist "%PYTHON_DIR%" (
        echo [Warning] Could not fully remove old installation
        echo [Warning] Some files may be locked. Continuing anyway...
        echo [Warning] Partial removal only >> "%VERBOSE_LOG%"
    )
)

echo [Check] Checking available disk space...
for /f "tokens=3" %%a in ('dir /-c ^| find "bytes free"') do set FREE_SPACE=%%a
echo [Info] Free disk space: %FREE_SPACE% bytes >> "%VERBOSE_LOG%"

echo.
echo This will download and set up Python (approx. 30 MB)
echo and install required packages (approx. 5 MB)
echo.
echo Total download: ~35 MB
echo This only needs to be done once.
echo.
echo Note: Detailed logs will be saved to:
echo - install_log.txt (errors)
echo - install_verbose.log (full diagnostic)
echo.
pause

REM ========================================
REM PREFERRED METHOD: Use Embeddable Python
REM This is more reliable and avoids registry issues
REM ========================================
echo.
echo ========================================
echo STEP 2: Installing Python (Embeddable)
echo ========================================
echo.
echo Using embeddable Python for maximum reliability...
echo This avoids conflicts with system Python installations.
echo.

set PYTHON_ZIP=python-%PYTHON_VERSION%-embed-amd64.zip

echo [Download] Downloading Python %PYTHON_VERSION% (embeddable)...
echo [Download] Starting download from: %PYTHON_EMBED_URL% >> "%VERBOSE_LOG%"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Write-Host 'Connecting...'; Invoke-WebRequest -Uri '%PYTHON_EMBED_URL%' -OutFile '%PYTHON_ZIP%' -TimeoutSec 120; Write-Host 'Download complete'; exit 0 } catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }}" 2>>"%VERBOSE_LOG%"

if not exist "%PYTHON_ZIP%" (
    echo.
    echo [Error] Failed to download Python
    echo [Error] Download failed >> "%VERBOSE_LOG%"
    echo.
    echo This could be due to:
    echo - Internet connection issues
    echo - Firewall blocking the download
    echo - Antivirus blocking the download
    echo.
    echo Please check install_verbose.log for details.
    echo.
    goto :TRY_FULL_INSTALLER
)

echo [OK] Download complete
echo.
echo [Extract] Extracting Python...
echo [Extract] Starting extraction >> "%VERBOSE_LOG%"

if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

powershell -Command "try { Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force; Write-Host 'Extraction complete'; exit 0 } catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }" 2>>"%VERBOSE_LOG%"

del "%PYTHON_ZIP%" 2>nul

if not exist "%PYTHON_DIR%\python.exe" (
    echo [Error] Extraction failed
    echo [Error] python.exe not found after extraction >> "%VERBOSE_LOG%"
    goto :TRY_FULL_INSTALLER
)

echo [OK] Python extracted successfully
echo.

echo [Configure] Enabling pip support...
echo [Configure] Modifying python311._pth >> "%VERBOSE_LOG%"

REM Enable site-packages for pip
powershell -Command "try { $content = Get-Content '%PYTHON_DIR%\python311._pth'; $content = $content -replace '#import site', 'import site'; $content | Set-Content '%PYTHON_DIR%\python311._pth'; Write-Host 'Configuration updated'; exit 0 } catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }" 2>>"%VERBOSE_LOG%"

echo [OK] Python configured
echo.

echo [Setup] Installing pip...
echo [Setup] Downloading get-pip.py >> "%VERBOSE_LOG%"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'; exit 0 } catch { exit 1 }}" 2>>"%VERBOSE_LOG%"

if exist "get-pip.py" (
    echo [Setup] Running pip installer...
    echo [Setup] Installing pip >> "%VERBOSE_LOG%"
    "%PYTHON_DIR%\python.exe" get-pip.py >>"%VERBOSE_LOG%" 2>&1
    del get-pip.py 2>nul
)

echo [OK] Pip installed
echo.

REM Test Python
echo [Test] Verifying Python installation...
"%PYTHON_DIR%\python.exe" --version >>"%VERBOSE_LOG%" 2>&1
if errorlevel 1 (
    echo [Error] Python verification failed
    goto :TRY_FULL_INSTALLER
)

"%PYTHON_DIR%\python.exe" --version
echo [OK] Python is working!
echo.

echo [Note] Using embeddable Python
echo       tkinter (GUI) is not available in this version
echo       The agent will work with limited GUI features
echo.

goto :INSTALL_PACKAGES

REM ========================================
REM FALLBACK: Try Full Installer
REM Only if embeddable method fails
REM ========================================
:TRY_FULL_INSTALLER
echo.
echo ========================================
echo STEP 2B: Trying Full Installer (Fallback)
echo ========================================
echo.
echo Embeddable Python failed, trying full installer...
echo.

echo [Download] Downloading full Python installer...
echo [Download] Full installer from: %PYTHON_URL% >> "%VERBOSE_LOG%"

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -TimeoutSec 120; exit 0 } catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }}" 2>>"%VERBOSE_LOG%"

if not exist "%PYTHON_INSTALLER%" (
    echo [Error] Could not download installer
    echo [Error] Full installer download failed >> "%VERBOSE_LOG%"
    goto :INSTALLATION_FAILED
)

echo [OK] Installer downloaded
echo.

REM Clean target directory completely
if exist "%PYTHON_DIR%" (
    echo [Cleanup] Removing target directory...
    rmdir /s /q "%PYTHON_DIR%" 2>nul
    timeout /t 2 /nobreak >nul
)

echo [Install] Installing Python (this may take 2-3 minutes)...
echo [Install] Starting installation >> "%VERBOSE_LOG%"
echo [Install] Command: %PYTHON_INSTALLER% /quiet /log "%INSTALL_LOG%" InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0 CompileAll=0 >> "%VERBOSE_LOG%"
echo.
echo Please wait...
echo.

REM Try silent installation with log
"%PYTHON_INSTALLER%" /quiet /log "%INSTALL_LOG%" InstallAllUsers=0 TargetDir="%PYTHON_DIR%" Include_pip=1 Include_tcltk=1 Include_test=0 PrependPath=0 Shortcuts=0 AssociateFiles=0 CompileAll=0

REM Wait longer for installation
echo [Wait] Waiting for installation to complete...
timeout /t 10 /nobreak >nul

REM Check if installation succeeded
if exist "%PYTHON_DIR%\python.exe" (
    echo [Test] Verifying installation...
    "%PYTHON_DIR%\python.exe" --version >>"%VERBOSE_LOG%" 2>&1
    if not errorlevel 1 (
        echo [OK] Installation successful!
        del "%PYTHON_INSTALLER%" 2>nul

        REM Test tkinter
        "%PYTHON_DIR%\python.exe" -c "import tkinter" >nul 2>&1
        if not errorlevel 1 (
            echo [OK] tkinter available (full GUI support)
        )

        goto :INSTALL_PACKAGES
    )
)

echo [Error] Installation did not complete successfully
echo [Error] Full installer failed, python.exe not found or not working >> "%VERBOSE_LOG%"

del "%PYTHON_INSTALLER%" 2>nul

goto :INSTALLATION_FAILED

REM ========================================
REM Install Required Packages
REM ========================================
:INSTALL_PACKAGES
echo.
echo ========================================
echo STEP 3: Installing Packages
echo ========================================
echo.

echo [Packages] Checking pip...
"%PYTHON_DIR%\python.exe" -m pip --version >>"%VERBOSE_LOG%" 2>&1
if errorlevel 1 (
    echo [Error] pip is not available
    echo [Error] pip not working >> "%VERBOSE_LOG%"
    goto :INSTALLATION_FAILED
)

echo [OK] pip is available
echo.

echo [Packages] Updating pip...
"%PYTHON_DIR%\python.exe" -m pip install --upgrade pip --quiet >>"%VERBOSE_LOG%" 2>&1

echo [Packages] Installing python-socketio and requests...
echo [Packages] Installing python-socketio requests >> "%VERBOSE_LOG%"

"%PYTHON_DIR%\python.exe" -m pip install --no-warn-script-location python-socketio requests --quiet >>"%VERBOSE_LOG%" 2>&1

if errorlevel 1 (
    echo [Warning] Package installation had issues
    echo.
    echo Retrying with verbose output...
    "%PYTHON_DIR%\python.exe" -m pip install python-socketio requests

    if errorlevel 1 (
        echo [Error] Failed to install packages
        echo.
        echo Please check install_verbose.log for details
        pause
        exit /b 1
    )
)

echo [OK] Packages installed successfully
echo.

REM Final verification
echo [Verify] Final system check...
"%PYTHON_DIR%\python.exe" -c "import socketio; import requests; print('All imports OK')" >>"%VERBOSE_LOG%" 2>&1
if errorlevel 1 (
    echo [Error] Package verification failed
    goto :INSTALLATION_FAILED
)

goto :COMPLETE

REM ========================================
REM Installation Complete
REM ========================================
:COMPLETE
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.

echo Python location: %PYTHON_DIR%
echo.

echo Installed version:
"%PYTHON_DIR%\python.exe" --version

echo.
echo Installed packages:
"%PYTHON_DIR%\python.exe" -m pip list 2>nul | findstr /i "socketio requests"

echo.
echo ========================================
echo You can now run start_agent.bat
echo ========================================
echo.

REM Save success marker
echo SUCCESS > "%PYTHON_DIR%\installation_complete.txt"
echo Installation completed at: %date% %time% >> "%PYTHON_DIR%\installation_complete.txt"

pause
exit /b 0

REM ========================================
REM Installation Failed
REM ========================================
:INSTALLATION_FAILED
echo.
echo ========================================
echo Installation Failed
echo ========================================
echo.
echo Automatic installation could not complete.
echo.
echo TROUBLESHOOTING STEPS:
echo.
echo 1. Check the log files:
echo    - install_verbose.log (detailed diagnostics)
echo    - install_log.txt (installer errors, if available)
echo.
echo 2. Common issues and solutions:
echo.
echo    [Antivirus Blocking]
echo    - Temporarily disable antivirus
echo    - Add exception for this folder
echo    - Try again
echo.
echo    [Registry Conflicts]
echo    - If you see "Modify/Repair/Uninstall" dialog:
echo      * Close it without selecting anything
echo      * Delete python_embed folder completely
echo      * Run this installer again
echo.
echo    [Disk Space]
echo    - Ensure at least 100 MB free space
echo    - Check disk quota if on network drive
echo.
echo    [Permissions]
echo    - Run from a folder you own (not Program Files)
echo    - Avoid network drives if possible
echo.
echo 3. Manual installation option:
echo    - Download Python 3.11.9 from python.org
echo    - Install to: %PYTHON_DIR%
echo    - Run this script again
echo.
echo 4. Contact support:
echo    - Send install_verbose.log to support
echo    - Describe which step failed
echo.
pause
exit /b 1
