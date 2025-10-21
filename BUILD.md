# SACMES Agent Build Instructions

## Prerequisites

Install PyInstaller:
```bash
pip install pyinstaller
```

## Build Executable

Using the minimal spec file (recommended):
```bash
pyinstaller agent_minimal.spec
```

The executable will be created in the `dist/` directory.

## Build System

- agent_minimal.spec: PyInstaller configuration (minimal, optimized)
- agent.py: Main agent source code
- Netzlab.ico: Application icon

## Release Process

1. Build executable locally: `pyinstaller agent_minimal.spec`
2. Test the executable
3. Create a new GitHub release with version tag (e.g., v1.0.0)
4. Upload the executable to the release
5. Users download from GitHub releases page

## Download from GitHub

Users should download the agent from:
https://github.com/lizchen2025/SACMES_Web/releases

This provides:
- Transparent source code review
- Version history
- Reduced false positives from antivirus software
- Direct download link for web application
