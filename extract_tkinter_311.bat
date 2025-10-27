@echo off
setlocal enabledelayedexpansion

REM Extract tkinter from Python 3.11.9 installer

title Extract tkinter from Python 3.11.9

set PYTHON_VERSION=3.11.9
set SCRIPT_DIR=%~dp0
set PYTHON_FILENAME=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_LOCAL=%SCRIPT_DIR%%PYTHON_FILENAME%
set TEMP_INSTALL=%SCRIPT_DIR%temp_python311_install
set EXTRACT_DIR=%SCRIPT_DIR%tkinter_package

REM Change to script directory
cd /d "%SCRIPT_DIR%"

echo ========================================
echo Extract tkinter from Python 3.11.9
echo ========================================
echo.
echo This script will:
echo   1. Install Python 3.11.9 temporarily
echo   2. Extract tkinter files
echo   3. Clean up temporary installation
echo.
echo Time required: 5-10 minutes
echo.
echo Working directory: %SCRIPT_DIR%
echo Installation will use: %TEMP_INSTALL%
echo.

REM Safety check: Ensure we're not in a system directory
echo %SCRIPT_DIR% | find /i "System32" >nul
if %errorlevel% equ 0 (
    echo [ERROR] Script is running from System32 directory
    echo This will cause installation to fail.
    echo.
    echo Please run this script from its actual location:
    echo E:\SACMES_web\web\SACMES_Web-Multiuser\
    echo.
    pause
    exit /b 1
)

echo %SCRIPT_DIR% | find /i "Windows" >nul
if %errorlevel% equ 0 (
    echo [WARNING] Script appears to be running from Windows directory
    echo This may cause permission issues.
    echo.
    pause
)

pause

REM Check if installer exists
if not exist "%PYTHON_LOCAL%" (
    echo [ERROR] %PYTHON_FILENAME% not found
    echo Expected location: %PYTHON_LOCAL%
    echo.
    echo Please run download_python311.bat first
    echo.
    pause
    exit /b 1
)

echo [OK] Python installer found: %PYTHON_FILENAME%

echo.
echo ========================================
echo Step 1/4: Install Python temporarily
echo ========================================
echo.

REM Clean up old temporary installation
if exist "%TEMP_INSTALL%" (
    echo Removing old temporary installation...
    rmdir /s /q "%TEMP_INSTALL%" 2>nul
    timeout /t 2 /nobreak >nul
)

echo Installing Python to: %TEMP_INSTALL%
echo This will take 2-3 minutes...
echo.

"%PYTHON_LOCAL%" /passive TargetDir="%TEMP_INSTALL%" Include_tcltk=1 PrependPath=0 AssociateFiles=0 Shortcuts=0

echo Waiting for installation to complete...
timeout /t 20 /nobreak >nul

if not exist "%TEMP_INSTALL%\python.exe" (
    echo.
    echo [ERROR] Installation failed
    echo.
    echo Troubleshooting:
    echo   - Run this script as Administrator
    echo   - Disable antivirus temporarily
    echo   - Ensure you have 500MB free disk space
    echo.
    pause
    exit /b 1
)

echo [OK] Python installed

echo.
echo ========================================
echo Step 2/4: Extract tkinter files
echo ========================================
echo.

REM Backup old extraction
if exist "%EXTRACT_DIR%" (
    echo Backing up old tkinter_package...
    if exist "%EXTRACT_DIR%.backup" rmdir /s /q "%EXTRACT_DIR%.backup" 2>nul
    move "%EXTRACT_DIR%" "%EXTRACT_DIR%.backup" >nul 2>&1
)

REM Create directory structure
mkdir "%EXTRACT_DIR%\Lib" 2>nul
mkdir "%EXTRACT_DIR%\DLLs" 2>nul
mkdir "%EXTRACT_DIR%\tcl" 2>nul

echo [1/3] Extracting tkinter library...
if exist "%TEMP_INSTALL%\Lib\tkinter" (
    xcopy "%TEMP_INSTALL%\Lib\tkinter" "%EXTRACT_DIR%\Lib\tkinter\" /E /I /Y >nul 2>&1
    echo       [OK] tkinter library extracted
) else (
    echo       [ERROR] tkinter not found
    pause
    exit /b 1
)

echo [2/3] Extracting tcl/tk runtime...
if exist "%TEMP_INSTALL%\tcl" (
    xcopy "%TEMP_INSTALL%\tcl" "%EXTRACT_DIR%\tcl\" /E /I /Y >nul 2>&1
    echo       [OK] tcl/tk runtime extracted
) else (
    echo       [WARN] tcl folder not found
)

echo [3/3] Extracting DLL files...
if exist "%TEMP_INSTALL%\DLLs\_tkinter.pyd" (
    copy "%TEMP_INSTALL%\DLLs\_tkinter.pyd" "%EXTRACT_DIR%\DLLs\" >nul 2>&1
    echo       [OK] _tkinter.pyd
)
copy "%TEMP_INSTALL%\DLLs\tcl*.dll" "%EXTRACT_DIR%\DLLs\" >nul 2>&1
copy "%TEMP_INSTALL%\DLLs\tk*.dll" "%EXTRACT_DIR%\DLLs\" >nul 2>&1
echo       [OK] tcl/tk DLLs

echo.
echo ========================================
echo Step 3/4: Verify extraction
echo ========================================
echo.

set VERIFY_OK=1

if exist "%EXTRACT_DIR%\Lib\tkinter\__init__.py" (
    echo [OK] tkinter library
) else (
    echo [ERROR] tkinter library missing
    set VERIFY_OK=0
)

if exist "%EXTRACT_DIR%\DLLs\_tkinter.pyd" (
    echo [OK] _tkinter.pyd
) else (
    echo [ERROR] _tkinter.pyd missing
    set VERIFY_OK=0
)

if exist "%EXTRACT_DIR%\DLLs\tcl86t.dll" (
    echo [OK] tcl86t.dll
) else (
    echo [ERROR] tcl86t.dll missing
    set VERIFY_OK=0
)

if exist "%EXTRACT_DIR%\DLLs\tk86t.dll" (
    echo [OK] tk86t.dll
) else (
    echo [ERROR] tk86t.dll missing
    set VERIFY_OK=0
)

if exist "%EXTRACT_DIR%\tcl\tcl8.6" (
    echo [OK] tcl runtime
) else (
    echo [ERROR] tcl runtime missing
    set VERIFY_OK=0
)

echo.
echo ========================================
echo Step 4/4: Cleanup
echo ========================================
echo.

echo Removing temporary installation...
rmdir /s /q "%TEMP_INSTALL%" 2>nul
echo [OK] Cleanup complete

echo.
echo ========================================
if %VERIFY_OK% equ 1 (
    echo Extraction Complete - SUCCESS
) else (
    echo Extraction Complete - WITH ERRORS
)
echo ========================================
echo.

REM Calculate size
set TOTAL_SIZE=0
for /r "%EXTRACT_DIR%" %%f in (*) do set /a TOTAL_SIZE+=%%~zf
set /a SIZE_MB=!TOTAL_SIZE!/1048576

echo Extracted to: %EXTRACT_DIR%
echo Size: ~!SIZE_MB! MB
echo.

if %VERIFY_OK% equ 1 (
    echo Status: All required files extracted successfully
    echo.
    echo Next: Run package_final.bat to create distribution package
) else (
    echo Status: Some files are missing - please review errors above
)

echo.
pause
