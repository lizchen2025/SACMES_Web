@echo off
REM Test extraction environment before running extract_tkinter_311.bat

title Test Extraction Environment

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo ========================================
echo Extraction Environment Test
echo ========================================
echo.
echo This script verifies that your environment is ready for
echo automatic tkinter extraction.
echo.
pause

set PASS=0
set FAIL=0

echo.
echo ========================================
echo Test 1: Script Location
echo ========================================
echo.
echo Script directory: %SCRIPT_DIR%
echo.

echo %SCRIPT_DIR% | find /i "System32" >nul
if %errorlevel% equ 0 (
    echo [FAIL] Script is in System32 directory
    echo This will cause extraction to fail.
    echo.
    echo Please copy all files to a user directory like:
    echo   C:\Users\YourName\Desktop\SACMES\
    echo   D:\Projects\SACMES\
    set /a FAIL+=1
) else (
    echo [PASS] Script location is valid
    set /a PASS+=1
)

echo.
echo ========================================
echo Test 2: Write Permissions
echo ========================================
echo.

echo Testing write permissions in script directory...
echo test > "%SCRIPT_DIR%test_write_permission.tmp" 2>nul

if exist "%SCRIPT_DIR%test_write_permission.tmp" (
    del "%SCRIPT_DIR%test_write_permission.tmp"
    echo [PASS] Write permissions OK
    set /a PASS+=1
) else (
    echo [FAIL] No write permissions
    echo Cannot write to: %SCRIPT_DIR%
    echo.
    echo Solutions:
    echo   - Run this script as Administrator
    echo   - Move files to a user-writable location
    set /a FAIL+=1
)

echo.
echo ========================================
echo Test 3: Disk Space
echo ========================================
echo.

for /f "tokens=3" %%a in ('dir "%SCRIPT_DIR%" ^| find "bytes free"') do set FREE_BYTES=%%a
set FREE_BYTES=%FREE_BYTES:,=%
set /a FREE_MB=%FREE_BYTES%/1048576

echo Free space: %FREE_MB% MB

if %FREE_MB% geq 500 (
    echo [PASS] Sufficient disk space
    set /a PASS+=1
) else (
    echo [FAIL] Insufficient disk space
    echo Need at least 500 MB free
    echo Currently have: %FREE_MB% MB
    set /a FAIL+=1
)

echo.
echo ========================================
echo Test 4: Python Installer
echo ========================================
echo.

if exist "%SCRIPT_DIR%python-3.11.9-amd64.exe" (
    echo [PASS] Python installer found
    for %%A in ("%SCRIPT_DIR%python-3.11.9-amd64.exe") do (
        set SIZE=%%~zA
        set /a SIZE_MB=!SIZE!/1048576
    )
    echo File: python-3.11.9-amd64.exe
    echo Size: !SIZE_MB! MB
    set /a PASS+=1
) else (
    echo [FAIL] Python installer not found
    echo Expected: %SCRIPT_DIR%python-3.11.9-amd64.exe
    echo.
    echo Run download_python311.bat first
    set /a FAIL+=1
)

echo.
echo ========================================
echo Test 5: Required Scripts
echo ========================================
echo.

if exist "%SCRIPT_DIR%extract_tkinter_311.bat" (
    echo [PASS] extract_tkinter_311.bat found
    set /a PASS+=1
) else (
    echo [FAIL] extract_tkinter_311.bat not found
    set /a FAIL+=1
)

echo.
echo ========================================
echo Test Results
echo ========================================
echo.
echo Tests passed: %PASS%
echo Tests failed: %FAIL%
echo.

if %FAIL% equ 0 (
    echo ========================================
    echo ALL TESTS PASSED
    echo ========================================
    echo.
    echo Your environment is ready for automatic extraction.
    echo.
    echo Next step: Run extract_tkinter_311.bat
    echo.
) else (
    echo ========================================
    echo TESTS FAILED
    echo ========================================
    echo.
    echo Please resolve the issues above before running extract_tkinter_311.bat
    echo.
    echo If automatic extraction continues to fail, use the manual method:
    echo See: MANUAL_EXTRACTION_GUIDE.txt
    echo.
)

pause
