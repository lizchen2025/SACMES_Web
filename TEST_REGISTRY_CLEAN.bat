@echo off
REM Test if Python 3.11 registry entries are cleaned

title Test Registry Clean

echo ========================================
echo Python 3.11 Registry Test
echo ========================================
echo.
echo Checking for Python 3.11 registry entries...
echo.

set FOUND=0

REM Check HKEY_CURRENT_USER
reg query "HKCU\Software\Python\PythonCore\3.11" >nul 2>&1
if %errorlevel% equ 0 (
    echo [FOUND] HKCU\Software\Python\PythonCore\3.11
    set FOUND=1
) else (
    echo [CLEAN] HKCU\Software\Python\PythonCore\3.11 - Not found
)

REM Check HKEY_LOCAL_MACHINE
reg query "HKLM\Software\Python\PythonCore\3.11" >nul 2>&1
if %errorlevel% equ 0 (
    echo [FOUND] HKLM\Software\Python\PythonCore\3.11
    set FOUND=1
) else (
    echo [CLEAN] HKLM\Software\Python\PythonCore\3.11 - Not found
)

REM Check WOW6432Node
reg query "HKLM\Software\WOW6432Node\Python\PythonCore\3.11" >nul 2>&1
if %errorlevel% equ 0 (
    echo [FOUND] HKLM\Software\WOW6432Node\Python\PythonCore\3.11
    set FOUND=1
) else (
    echo [CLEAN] HKLM\Software\WOW6432Node\Python\PythonCore\3.11 - Not found
)

echo.
echo ========================================
if %FOUND% equ 0 (
    echo Result: CLEAN
    echo ========================================
    echo.
    echo All Python 3.11 registry entries have been removed.
    echo You can now proceed with tkinter extraction.
) else (
    echo Result: REGISTRY ENTRIES STILL PRESENT
    echo ========================================
    echo.
    echo Some Python 3.11 registry entries still exist.
    echo This may cause conflicts during installation.
    echo.
    echo Try running CLEAN_PYTHON311_REGISTRY.bat as Administrator.
)
echo.
pause
