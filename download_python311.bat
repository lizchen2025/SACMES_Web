@echo off
REM Download Python 3.11.9 Full Installer

title Download Python 3.11.9

set PYTHON_VERSION=3.11.9
set SCRIPT_DIR=%~dp0
set PYTHON_FILENAME=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_LOCAL=%SCRIPT_DIR%%PYTHON_FILENAME%
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_FILENAME%

cd /d "%SCRIPT_DIR%"

echo ========================================
echo Download Python 3.11.9 Installer
echo ========================================
echo.
echo Version: %PYTHON_VERSION%
echo File: python-%PYTHON_VERSION%-amd64.exe
echo Download location: %SCRIPT_DIR%
echo Size: Approximately 30 MB
echo.

if exist "%PYTHON_LOCAL%" (
    echo File already exists: %PYTHON_FILENAME%
    echo.
    for %%A in ("%PYTHON_LOCAL%") do set SIZE=%%~zA
    set /a SIZE_MB=!SIZE!/1048576
    echo Size: !SIZE_MB! MB
    echo.
    choice /C YN /M "Re-download"
    if errorlevel 2 goto :skip_download
    echo.
)

echo Downloading...
echo URL: %PYTHON_URL%
echo Note: The window may appear frozen during download.
echo This is normal - the download is running in the background.
echo.

powershell -ExecutionPolicy Bypass -Command "& {$ProgressPreference = 'Continue'; Write-Host 'Starting download...'; $start = Get-Date; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_LOCAL%' -UseBasicParsing; $elapsed = (Get-Date) - $start; Write-Host ('Download completed in {0:N0} seconds' -f $elapsed.TotalSeconds)}"

if not exist "%PYTHON_LOCAL%" (
    echo.
    echo [ERROR] Download failed
    echo URL was: %PYTHON_URL%
    pause
    exit /b 1
)

:skip_download
echo.
echo ========================================
echo Download Complete
echo ========================================
echo.
echo File: %PYTHON_FILENAME%
for %%A in ("%PYTHON_LOCAL%") do set SIZE=%%~zA
set /a SIZE_MB=!SIZE!/1048576
echo Size: !SIZE_MB! MB
echo Location: %SCRIPT_DIR%
echo.
echo Next: Run extract_tkinter_311.bat to extract tkinter files
echo.
pause
