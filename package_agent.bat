@echo off
REM Manual script to package agent for distribution
REM Run this when you update agent files

echo ========================================
echo Packaging SACMES Agent
echo ========================================
echo.

REM Ensure downloads directory exists
if not exist "static\downloads" mkdir "static\downloads"

REM Remove old ZIP if exists
if exist "static\downloads\SACMES_Agent.zip" del "static\downloads\SACMES_Agent.zip"

REM Create new ZIP
echo Creating SACMES_Agent.zip...
powershell -Command "Compress-Archive -Path 'agent.py','start_agent.bat','install_python.bat','AGENT_README.txt','Netzlab.ico' -DestinationPath 'static/downloads/SACMES_Agent.zip' -Force"

if exist "static\downloads\SACMES_Agent.zip" (
    echo.
    echo ========================================
    echo Package created successfully!
    echo ========================================
    echo.
    echo Location: static\downloads\SACMES_Agent.zip

    REM Show file size
    for %%A in ("static\downloads\SACMES_Agent.zip") do (
        set size=%%~zA
        set /A sizeKB=!size! / 1024
        echo Size: !sizeKB! KB
    )

    echo.
    echo Next steps:
    echo 1. git add static/downloads/SACMES_Agent.zip
    echo 2. git commit -m "Update agent package"
    echo 3. git push origin mul
    echo.
) else (
    echo.
    echo ERROR: Failed to create package
    echo.
)

pause
