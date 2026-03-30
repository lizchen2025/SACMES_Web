@echo off
echo ================================================================
echo SACMES Local - Clear Python Cache
echo ================================================================
echo.
echo Clearing Python cache files...
cd /d "%~dp0"
del /s /q *.pyc 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo.
echo [OK] Cache cleared successfully
echo.
echo Now you can run START.bat to restart the application
echo.
pause
