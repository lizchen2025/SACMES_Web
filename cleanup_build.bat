@echo off
REM Cleanup script for SACMES Agent build artifacts
REM Run this to clean up after building the agent EXE

echo Cleaning up build artifacts...
echo.

if exist agent_build_env (
    echo Removing agent_build_env...
    rmdir /s /q agent_build_env
)

if exist build (
    echo Removing build...
    rmdir /s /q build
)

if exist dist (
    echo Removing dist...
    rmdir /s /q dist
)

if exist __pycache__ (
    echo Removing __pycache__...
    rmdir /s /q __pycache__
)

if exist agent.json (
    echo Removing agent.json...
    del /q agent.json
)

if exist *.log (
    echo Removing log files...
    del /q *.log
)

echo.
echo Cleanup complete!
pause
