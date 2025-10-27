@echo off
REM Clean Python 3.11 Registry Entries
REM This script removes Python 3.11 registry entries to avoid conflicts

title Clean Python 3.11 Registry

echo ========================================
echo Python 3.11 Registry Cleaner
echo ========================================
echo.
echo This script will remove Python 3.11 registry entries.
echo This does NOT uninstall Python, only cleans registry.
echo.
echo Registry keys to be removed:
echo   HKEY_CURRENT_USER\Software\Python\PythonCore\3.11
echo   HKEY_LOCAL_MACHINE\Software\Python\PythonCore\3.11
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Cleaning registry entries...
echo.

REM Clean HKEY_CURRENT_USER
reg delete "HKCU\Software\Python\PythonCore\3.11" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Removed HKCU\Software\Python\PythonCore\3.11
) else (
    echo [INFO] HKCU entry not found or already removed
)

REM Clean HKEY_LOCAL_MACHINE (requires admin)
reg delete "HKLM\Software\Python\PythonCore\3.11" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Removed HKLM\Software\Python\PythonCore\3.11
) else (
    echo [INFO] HKLM entry not found, already removed, or insufficient permissions
)

REM Clean HKEY_LOCAL_MACHINE for 32-bit keys on 64-bit system
reg delete "HKLM\Software\WOW6432Node\Python\PythonCore\3.11" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Removed HKLM\Software\WOW6432Node\Python\PythonCore\3.11
) else (
    echo [INFO] WOW6432Node entry not found or already removed
)

echo.
echo ========================================
echo Registry Cleanup Complete
echo ========================================
echo.
echo Run TEST_REGISTRY_CLEAN.bat to verify the cleanup.
echo.
pause
