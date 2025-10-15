@echo off
REM Kill all running agent processes before build

echo Checking for running agent processes...

tasklist /FI "IMAGENAME eq SACMES_Agent*.exe" 2>NUL | find /I /N "SACMES_Agent">NUL
if %errorlevel%==0 (
    echo Found running agent process, terminating...
    taskkill /F /IM "SACMES_Agent*.exe" 2>NUL
    timeout /t 2 >NUL
    echo Agent processes terminated.
) else (
    echo No running agent processes found.
)

tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq agent.py*" 2>NUL | find /I /N "python.exe">NUL
if %errorlevel%==0 (
    echo Found running Python agent script...
    echo Please close agent.py manually if running.
)

echo Done.
