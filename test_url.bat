@echo off
REM Quick test to verify Python download URL

set PYTHON_VERSION=3.11.9
set PYTHON_FILENAME=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_FILENAME%

echo Testing Python download URL...
echo.
echo URL: %PYTHON_URL%
echo.
echo Testing connectivity...

powershell -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -Uri '%PYTHON_URL%' -Method Head -UseBasicParsing; Write-Host '[OK] URL is valid'; Write-Host 'File size:' $response.Headers.'Content-Length' 'bytes' } catch { Write-Host '[ERROR] URL failed:' $_.Exception.Message }"

pause
