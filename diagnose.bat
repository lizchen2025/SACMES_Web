@echo off
REM SACMES Agent Diagnostic Tool
REM This script helps diagnose installation issues

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo SACMES Agent Diagnostic Tool
echo ========================================
echo.
echo Current time: %date% %time%
echo Script location: %SCRIPT_DIR%
echo Working directory: %CD%
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% == 0 (
    echo Running as: Administrator
) else (
    echo Running as: Normal user
)
echo.

echo ========================================
echo FILE CHECK
echo ========================================
echo.

echo Required files:
if exist "%SCRIPT_DIR%agent.py" (
    echo [OK] agent.py
) else (
    echo [MISSING] agent.py
)

if exist "%SCRIPT_DIR%start_agent.bat" (
    echo [OK] start_agent.bat
) else (
    echo [MISSING] start_agent.bat
)

if exist "%SCRIPT_DIR%install_python.bat" (
    echo [OK] install_python.bat
) else (
    echo [MISSING] install_python.bat
)

if exist "%SCRIPT_DIR%test_installation.bat" (
    echo [OK] test_installation.bat
) else (
    echo [MISSING] test_installation.bat
)

echo.

echo ========================================
echo PYTHON INSTALLATION CHECK
echo ========================================
echo.

if exist "%SCRIPT_DIR%sacmes_python" (
    echo [EXISTS] sacmes_python folder

    if exist "%SCRIPT_DIR%sacmes_python\python.exe" (
        echo [OK] python.exe found

        echo.
        echo Testing Python:
        "%SCRIPT_DIR%sacmes_python\python.exe" --version 2>nul
        if errorlevel 1 (
            echo [ERROR] Python is not working
        ) else (
            echo [OK] Python works

            echo.
            echo Testing tkinter:
            "%SCRIPT_DIR%sacmes_python\python.exe" -c "import tkinter; print('tkinter OK')" 2>nul
            if errorlevel 1 (
                echo [MISSING] tkinter not available
            ) else (
                echo [OK] tkinter available
            )

            echo.
            echo Testing packages:
            "%SCRIPT_DIR%sacmes_python\python.exe" -m pip show python-socketio >nul 2>&1
            if errorlevel 1 (
                echo [MISSING] python-socketio
            ) else (
                echo [OK] python-socketio installed
            )

            "%SCRIPT_DIR%sacmes_python\python.exe" -m pip show requests >nul 2>&1
            if errorlevel 1 (
                echo [MISSING] requests
            ) else (
                echo [OK] requests installed
            )
        )
    ) else (
        echo [MISSING] python.exe not found in sacmes_python folder
    )
) else (
    echo [NOT INSTALLED] sacmes_python folder does not exist
)

echo.

REM Check for old installation folders
if exist "%SCRIPT_DIR%python_embed" (
    echo [WARNING] Found old python_embed folder from previous version
    echo           You should delete this folder
)

echo.

echo ========================================
echo REGISTRY CHECK
echo ========================================
echo.
echo Scanning for Python installation records...
echo.

powershell -Command "$ErrorActionPreference='SilentlyContinue'; $regPaths = @('HKCU:\Software\Python\PythonCore\3.11', 'HKLM:\Software\Python\PythonCore\3.11', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'); $foundAny = $false; foreach($path in $regPaths) { if(Test-Path $path) { $items = Get-ChildItem $path -ErrorAction SilentlyContinue; foreach($item in $items) { $props = Get-ItemProperty $item.PSPath -ErrorAction SilentlyContinue; if($props.InstallLocation -like '*sacmes_python*' -or $props.InstallLocation -like '*python_embed*' -or $props.DisplayName -like '*Python 3.11*') { Write-Host 'Found Python registry entry:'; Write-Host \"  Registry: $($item.PSPath)\"; if($props.DisplayName) { Write-Host \"  Name: $($props.DisplayName)\" } if($props.InstallLocation) { Write-Host \"  Location: $($props.InstallLocation)\" } if($props.InstallLocation -like '*sacmes_python*' -or $props.InstallLocation -like '*python_embed*') { Write-Host '  STATUS: CONFLICT - This may cause installation issues' -ForegroundColor Red } else { Write-Host '  STATUS: OK - Different installation' -ForegroundColor Green } Write-Host ''; $foundAny = $true } } } } if(-not $foundAny) { Write-Host 'No Python-related registry entries found.' -ForegroundColor Green; Write-Host 'Registry is clean!' }"

echo.

echo ========================================
echo LOG FILES
echo ========================================
echo.

if exist "%SCRIPT_DIR%install_log.txt" (
    echo [EXISTS] install_log.txt
    for %%A in ("%SCRIPT_DIR%install_log.txt") do (
        echo Size: %%~zA bytes
        echo Modified: %%~tA
    )
    echo.
    echo Last 10 lines of install_log.txt:
    echo ----------------------------------------
    powershell -Command "Get-Content '%SCRIPT_DIR%install_log.txt' -Tail 10"
    echo ----------------------------------------
) else (
    echo [NOT FOUND] install_log.txt
    echo No installation has been attempted yet.
)

echo.

echo ========================================
echo RECOMMENDATIONS
echo ========================================
echo.

if not exist "%SCRIPT_DIR%sacmes_python" (
    echo 1. Python is not installed yet
    echo 2. Run start_agent.bat to install
    echo 3. Check install_log.txt if installation fails
) else (
    echo Installation appears complete!
    echo You can run start_agent.bat to launch the agent.
)

echo.

REM Check for conflicts
powershell -Command "$ErrorActionPreference='SilentlyContinue'; $regPaths = @('HKCU:\Software\Python\PythonCore\3.11', 'HKLM:\Software\Python\PythonCore\3.11', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'); $foundConflict = $false; foreach($path in $regPaths) { if(Test-Path $path) { Get-ChildItem $path -ErrorAction SilentlyContinue | ForEach-Object { $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue; if($props.InstallLocation -like '*sacmes_python*' -or $props.InstallLocation -like '*python_embed*') { $foundConflict = $true } } } } if($foundConflict) { Write-Host 'ISSUE DETECTED:' -ForegroundColor Red; Write-Host 'Registry contains conflicting Python installation records.'; Write-Host ''; Write-Host 'SOLUTION:' -ForegroundColor Yellow; Write-Host '1. Run install_python.bat as Administrator'; Write-Host '   (Right-click install_python.bat -> Run as administrator)'; Write-Host '2. This will clean the registry and reinstall Python'; Write-Host ''; Write-Host 'OR manually clean registry and delete these folders:'; Write-Host '- sacmes_python'; Write-Host '- python_embed (if exists)'; Write-Host 'Then run start_agent.bat again'; }"

echo.
echo ========================================
echo Diagnostic complete!
echo ========================================
echo.
pause
