# SACMES Agent Build Instructions

## Overview

This document provides instructions for building standalone executables of the SACMES Agent application.

## System Requirements

- Python 3.8 or later
- Windows operating system
- 500 MB free disk space for build environment

## Dependencies

The agent requires the following Python packages:
- python-socketio (5.x)
- requests (2.25+)

These dependencies are automatically installed during the build process.

## Build Methods

### Method 1: Standard Build (Recommended)

Creates a GUI-only executable without console output.

```batch
build_agent_minimal.bat
```

Output: `dist\SACMES_Agent_Minimal.exe`

### Method 2: Debug Build

Creates an executable with console window for debugging.

```batch
build_agent_console.bat
```

Output: `dist\SACMES_Agent_Debug.exe`

### Method 3: Alternative Build

Alternative build script using command-line parameters.

```batch
build_agent_exe.bat
```

Output: `dist\SACMES_Agent.exe`

## Build Process

Each build script performs the following steps:

1. Verifies Python installation
2. Creates isolated virtual environment
3. Installs required dependencies
4. Installs PyInstaller
5. Compiles Python code to executable
6. Packages all dependencies into single file

## Testing

Before deploying, test the built executable:

1. Run the executable
2. Verify GUI appears correctly
3. Test connection to server
4. Confirm file monitoring functionality

## Troubleshooting

### Build Fails

- Verify Python is in system PATH
- Check available disk space
- Disable antivirus temporarily during build

### Executable Fails to Run

- Test with debug build to view error messages
- Verify server URL is correct
- Check network connectivity

## Cleanup

Remove build artifacts after successful build:

```batch
cleanup_build.bat
```

This removes:
- Virtual environment
- Build cache
- Temporary files

## Distribution

The generated executable is self-contained and can be distributed as a single file. No Python installation is required on target systems.

Minimum target system requirements:
- Windows 7 or later
- 100 MB free disk space
- Network connectivity
