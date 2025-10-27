@echo off
setlocal enabledelayedexpansion

REM Create final distribution package

title Create SACMES Agent Distribution Package

echo ========================================
echo SACMES Agent - Create Distribution
echo ========================================
echo.

REM Configuration
set OUTPUT_ZIP=SACMES_Agent.zip
set TEMP_DIR=%CD%\package_temp

echo Checking prerequisites...
echo.

REM Check if tkinter_package exists
if not exist "%CD%\tkinter_package" (
    echo [ERROR] tkinter_package folder not found
    echo.
    echo Please run these scripts first:
    echo   1. download_python311.bat
    echo   2. extract_tkinter_311.bat
    echo.
    pause
    exit /b 1
)

if not exist "%CD%\tkinter_package\Lib\tkinter" (
    echo [ERROR] tkinter files not found in tkinter_package
    echo.
    echo Please run extract_tkinter_311.bat
    echo.
    pause
    exit /b 1
)

echo [OK] tkinter_package found

REM Check required files
set MISSING=0

if not exist "%CD%\agent.py" (
    echo [ERROR] agent.py not found
    set MISSING=1
)

if not exist "%CD%\start_agent.bat" (
    echo [ERROR] start_agent.bat not found
    set MISSING=1
)

if not exist "%CD%\install_portable_python.bat" (
    echo [ERROR] install_portable_python.bat not found
    set MISSING=1
)

if not exist "%CD%\download_file.ps1" (
    echo [ERROR] download_file.ps1 not found
    set MISSING=1
)

if not exist "%CD%\README.md" (
    echo [ERROR] README.md not found
    set MISSING=1
)

if %MISSING% equ 1 (
    echo.
    echo [ERROR] Required files are missing
    pause
    exit /b 1
)

echo [OK] All required files found
echo.

echo ========================================
echo Creating package
echo ========================================
echo.

REM Clean up old package
if exist "%OUTPUT_ZIP%" (
    echo Removing old package...
    del "%OUTPUT_ZIP%"
)

if exist "%TEMP_DIR%" (
    rmdir /s /q "%TEMP_DIR%"
)

REM Create temporary directory structure
mkdir "%TEMP_DIR%"

echo Copying files...
echo.

echo [1/6] Copying agent.py...
copy "%CD%\agent.py" "%TEMP_DIR%\" >nul

echo [2/6] Copying startup scripts...
copy "%CD%\start_agent.bat" "%TEMP_DIR%\" >nul
copy "%CD%\install_portable_python.bat" "%TEMP_DIR%\" >nul

echo [3/6] Copying utilities...
copy "%CD%\download_file.ps1" "%TEMP_DIR%\" >nul
if exist "%CD%\FIX_MISSING_PACKAGES.bat" (
    copy "%CD%\FIX_MISSING_PACKAGES.bat" "%TEMP_DIR%\" >nul
)

echo [4/6] Copying documentation...
copy "%CD%\README.md" "%TEMP_DIR%\" >nul

echo [5/6] Copying tkinter_package...
xcopy "%CD%\tkinter_package" "%TEMP_DIR%\tkinter_package\" /E /I /Y >nul 2>&1

echo [6/6] Creating ZIP archive...
powershell -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%TEMP_DIR%\*' -DestinationPath '%OUTPUT_ZIP%' -Force"

REM Clean up
rmdir /s /q "%TEMP_DIR%"

if not exist "%OUTPUT_ZIP%" (
    echo.
    echo [ERROR] Failed to create package
    pause
    exit /b 1
)

echo.
echo ========================================
echo Package Created Successfully
echo ========================================
echo.

REM Display package information
for %%A in ("%OUTPUT_ZIP%") do (
    set SIZE=%%~zA
    set /a SIZE_MB=!SIZE!/1048576
    echo File: %%~nxA
    echo Size: !SIZE_MB! MB
    echo Location: %%~fA
)

echo.
echo Package contents:
echo   - agent.py
echo   - start_agent.bat
echo   - install_portable_python.bat
echo   - download_file.ps1
echo   - tkinter_package/
echo   - README.md

echo.
echo ========================================
echo Next Steps
echo ========================================
echo.
choice /C YN /M "Copy package to static/downloads"

if errorlevel 2 goto :skip_copy

if not exist "static\downloads" (
    echo.
    echo [WARN] static\downloads folder not found
    echo Creating folder...
    mkdir "static\downloads"
)

copy /Y "%OUTPUT_ZIP%" "static\downloads\SACMES_Agent.zip" >nul

if exist "static\downloads\SACMES_Agent.zip" (
    echo [OK] Package copied to static\downloads\SACMES_Agent.zip
) else (
    echo [ERROR] Failed to copy package
)

:skip_copy

echo.
echo ========================================
echo Distribution package is ready
echo ========================================
echo.
echo Users should:
echo   1. Download and extract %OUTPUT_ZIP%
echo   2. Run start_agent.bat
echo   3. Follow on-screen instructions
echo.
pause
