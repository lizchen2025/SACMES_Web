# SACMES Agent - Minimal EXE Build Guide

This guide explains how to build the **smallest possible** standalone EXE for the SACMES agent.

## 📦 What Gets Packaged

The agent EXE includes:
- ✅ Full GUI interface (tkinter)
- ✅ Socket.IO client for server communication
- ✅ File monitoring and filtering system
- ✅ Python 3.8+ runtime (embedded)
- ✅ All necessary dependencies

**Total dependencies: Only 1 package** (`python-socketio`)

## 🎯 Build Methods

### Method 1: Ultra-Minimal (Recommended)
Uses optimized `.spec` file for the smallest possible EXE.

```batch
build_agent_minimal.bat
```

**Expected size:** ~15-25 MB (depending on Python version)

### Method 2: Standard Build
Basic PyInstaller build with command-line options.

```batch
build_agent_exe.bat
```

**Expected size:** ~20-30 MB

## 🔧 Prerequisites

1. **Python 3.8 or later** installed and in PATH
   - Download: https://www.python.org/downloads/
   - ⚠️ Check "Add Python to PATH" during installation

2. **Windows OS** (for .bat scripts)
   - Linux/Mac users: Adapt the commands to bash scripts

## 📝 Step-by-Step Build Process

### Step 1: Prepare Your Environment
```batch
cd e:\SACMES_web\web\SACMES_Web-Multiuser
```

### Step 2: Run Build Script
```batch
# Recommended method
build_agent_minimal.bat

# The script will:
# 1. Check for Python 3.8+
# 2. Create a clean virtual environment
# 3. Install ONLY python-socketio (minimal deps)
# 4. Install PyInstaller
# 5. Build the EXE using optimized settings
# 6. Show file size and location
```

### Step 3: Find Your EXE
```
Location: dist\SACMES_Agent_Minimal.exe
```

### Step 4: Test the EXE
```batch
dist\SACMES_Agent_Minimal.exe
```

## 🗂️ File Structure After Build

```
SACMES_Web-Multiuser/
├── agent.py                          # Source code
├── agent_minimal.spec                # PyInstaller spec (optimized)
├── build_agent_minimal.bat           # Build script (recommended)
├── build_agent_exe.bat               # Alternative build script
├── requirements_agent_minimal.txt    # Minimal dependencies list
├── BUILD_AGENT_README.md            # This file
├── agent_build_env/                 # Virtual environment (can delete after build)
├── build/                           # PyInstaller temp files (can delete)
└── dist/
    └── SACMES_Agent_Minimal.exe     # 🎉 YOUR FINAL EXE
```

## 🧹 Cleanup After Build

To save disk space, you can delete these folders after successful build:

```batch
rmdir /s /q agent_build_env
rmdir /s /q build
```

The `dist/SACMES_Agent_Minimal.exe` is all you need!

## 🚀 Distribution

### What to Share:
- ✅ **Only** `SACMES_Agent_Minimal.exe`
- ✅ No Python installation needed on target machines
- ✅ No dependencies to install
- ✅ Works on any Windows 7+ machine

### How to Share:
1. Copy `dist/SACMES_Agent_Minimal.exe` to target machine
2. Double-click to run
3. That's it!

## 🔍 Size Optimization Tips

The build is already optimized, but if you need it even smaller:

### Current Optimizations Applied:
- ✅ Only 1 package dependency (`python-socketio`)
- ✅ Excludes matplotlib, numpy, pandas, scipy, PIL
- ✅ Excludes test/doc modules
- ✅ Strips debug symbols
- ✅ No UPX compression (causes issues with some antivirus)
- ✅ Single-file mode (no external DLLs)

### Further Reduction (Advanced):
If you need an even smaller file, consider:

1. **Use Python 3.8** (smaller runtime than 3.11+)
2. **Use UPX compression** (edit `.spec` file: `upx=True`)
   - Warning: Some antivirus may flag UPX-compressed files
3. **Remove unused modules** from `python-socketio`
   - Advanced: Manually trim socketio package

## 🐛 Troubleshooting

### Build fails with "Python not found"
- Install Python 3.8+ and add to PATH
- Restart your terminal after installation

### Build fails with "No module named socketio"
- Virtual environment not activated correctly
- Try deleting `agent_build_env` folder and rebuild

### EXE size is larger than expected
- First build is always larger (includes all Python runtime)
- Expected range: 15-30 MB (this is normal for PyInstaller)
- Anything under 50 MB is excellent for a Python GUI app

### Antivirus flags the EXE
- This is normal for PyInstaller EXEs (false positive)
- You can:
  1. Add exception in antivirus
  2. Submit to antivirus company for whitelisting
  3. Code-sign the EXE (requires certificate)

### EXE won't run on other machines
- Ensure target machine is Windows 7+
- Some machines may need Visual C++ Redistributable
  - Download: https://support.microsoft.com/en-us/help/2977003

## 📊 Size Comparison

| Build Type | Size | Description |
|------------|------|-------------|
| **Minimal (spec)** | ~15-25 MB | Optimized, recommended |
| Standard | ~20-30 MB | Basic PyInstaller |
| With full env | ~100+ MB | Includes dev packages |

## 🎓 Technical Details

### Dependencies Tree:
```
agent.py
└── python-socketio (5.x)
    ├── engineio (4.x)
    ├── websocket-client (1.x)
    └── bidict (0.x)
```

**Note:** Using python-socketio 5.x (5.0.0-5.14.1) for maximum compatibility with Python 3.8 - 3.13+ and all PyPI mirrors

### Excluded Modules:
- matplotlib, numpy, pandas, scipy
- PIL/Pillow, IPython, notebook
- pytest, setuptools, distutils
- xml, email, html, urllib (unused parts)
- multiprocessing, asyncio (unused)

### What's Included:
- tkinter (GUI) - built into Python
- socketio - for server communication
- Standard library: os, re, time, json, threading, uuid, collections, datetime

## 📞 Support

If you encounter issues:
1. Check Python version: `python --version`
2. Check if virtual env activated: Look for `(agent_build_env)` in terminal
3. Try deleting all build folders and rebuild
4. Check antivirus logs for blocked operations

## 🆕 Version Compatibility

### Python Versions Supported:
- ✅ Python 3.8
- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13+

### Package Versions:
- `python-socketio`: 5.x (5.0.0-5.14.1, auto-selects latest from range)
- `pyinstaller`: Latest version compatible with your Python (auto-selects)

---

**Last Updated:** 2025-01-14
**Tested With:** Python 3.8 - 3.13+
**Platform:** Windows 10/11
