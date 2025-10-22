@echo off
REM Package SACMES Agent for Distribution
REM Creates a clean ZIP file with only necessary files

setlocal enabledelayedexpansion

echo ========================================
echo SACMES Agent Packager
echo ========================================
echo.

set OUTPUT_DIR=%CD%\agent_package
set OUTPUT_ZIP=SACMES_Agent.zip

REM Clean up old package
if exist "%OUTPUT_DIR%" (
    echo Removing old package directory...
    rmdir /s /q "%OUTPUT_DIR%"
)

if exist "%OUTPUT_ZIP%" (
    echo Removing old ZIP file...
    del "%OUTPUT_ZIP%"
)

REM Create package directory
echo Creating package directory...
mkdir "%OUTPUT_DIR%"

REM Copy required files
echo.
echo Copying files...
echo.

echo [1/6] agent.py
copy agent.py "%OUTPUT_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy agent.py
    goto :ERROR
)

echo [2/6] start_agent.bat
copy start_agent.bat "%OUTPUT_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy start_agent.bat
    goto :ERROR
)

echo [3/6] install_python.bat
copy install_python.bat "%OUTPUT_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy install_python.bat
    goto :ERROR
)

echo [4/6] test_installation.bat
copy test_installation.bat "%OUTPUT_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy test_installation.bat
    goto :ERROR
)

echo [5/6] Netzlab.ico
copy Netzlab.ico "%OUTPUT_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy Netzlab.ico
    goto :ERROR
)

echo [6/6] AGENT_README.txt (as README.txt)
copy AGENT_README.txt "%OUTPUT_DIR%\README.txt" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy AGENT_README.txt
    goto :ERROR
)

echo.
echo Creating ZIP archive...
echo.

REM Create ZIP using PowerShell
powershell -Command "Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath '%OUTPUT_ZIP%' -Force"

if not exist "%OUTPUT_ZIP%" (
    echo ERROR: Failed to create ZIP file
    goto :ERROR
)

REM Clean up temporary directory
echo Cleaning up...
rmdir /s /q "%OUTPUT_DIR%"

REM Show file size
echo.
echo ========================================
echo Package Created Successfully!
echo ========================================
echo.
echo File: %OUTPUT_ZIP%
echo.

REM Get file size
for %%A in ("%OUTPUT_ZIP%") do set SIZE=%%~zA
set /a SIZE_KB=%SIZE%/1024
echo Size: %SIZE_KB% KB

echo.
echo Contents:
echo - agent.py (Agent source code)
echo - start_agent.bat (Main launcher)
echo - install_python.bat (First-time setup with robust fallbacks)
echo - test_installation.bat (Installation verification tool)
echo - Netzlab.ico (Application icon)
echo - README.txt (User documentation)
echo.
echo This ZIP is ready for distribution!
echo Users can extract and run start_agent.bat to begin.
echo.
pause
exit /b 0

:ERROR
echo.
echo ========================================
echo Packaging Failed
echo ========================================
echo.
echo Please check that all required files exist.
echo.
pause
exit /b 1
