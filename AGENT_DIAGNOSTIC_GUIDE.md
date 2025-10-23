# SACMES Agent v3.0 - Diagnostic Guide

## Overview

Version 3.0 introduces enhanced logging and diagnostics to troubleshoot installation issues. This guide explains how to use the logs to identify and fix problems.

## Key Changes in v3.0

### Installation Strategy Change

**Previous versions**:
- Full installer first → embeddable fallback
- Often caused registry conflicts showing "Modify/Repair/Uninstall" dialog

**Version 3.0**:
- **Embeddable Python first** (primary method)
- Full installer only as fallback
- Avoids registry conflicts completely

### Enhanced Logging

Two log files are now created:

1. **install_verbose.log** - Complete diagnostic log
   - Every step of installation
   - Timestamps
   - System information
   - All commands executed
   - All error messages

2. **install_log.txt** - Installer-specific errors
   - Only created if full installer is used
   - Contains Windows installer error codes

## Understanding the Installation Process

### STEP 1: System Check

```
[Check] Looking for existing Python installation...
[Test] Testing existing Python...
```

**What it does**:
- Checks if `python_embed` folder exists
- Tests if existing Python works
- Verifies packages are installed
- Removes corrupted installations

**Success**: Skips to package installation
**Failure**: Proceeds to STEP 2

### STEP 2: Installing Python (Embeddable)

```
[Download] Downloading Python 3.11.9 (embeddable)...
[Extract] Extracting Python...
[Configure] Enabling pip support...
[Setup] Installing pip...
[Test] Verifying Python installation...
```

**What it does**:
- Downloads ~11 MB ZIP file
- Extracts to `python_embed` folder
- Configures `python311._pth` to enable pip
- Downloads and installs pip
- Verifies Python works

**Success**: Goes to STEP 3
**Failure**: Goes to STEP 2B (fallback)

### STEP 2B: Trying Full Installer (Fallback)

```
[Download] Downloading full Python installer...
[Cleanup] Removing target directory...
[Install] Installing Python...
[Wait] Waiting for installation to complete...
```

**What it does**:
- Downloads ~30 MB installer
- Completely cleans target directory
- Runs silent installation
- Waits 10 seconds for completion
- Verifies installation

**Success**: Goes to STEP 3
**Failure**: Shows error and troubleshooting steps

### STEP 3: Installing Packages

```
[Packages] Checking pip...
[Packages] Updating pip...
[Packages] Installing python-socketio and requests...
[Verify] Final system check...
```

**What it does**:
- Verifies pip is available
- Updates pip to latest version
- Installs required packages
- Verifies packages can be imported

**Success**: Installation complete!
**Failure**: Shows error with log file references

## Common Issues and Solutions

### Issue 1: "Modify/Repair/Uninstall" Dialog Appears

**Symptoms**:
- Python installer window opens with three buttons
- No progress, just options to modify/repair/uninstall

**Cause**:
- Windows registry has entry for Python at target location
- Usually from previous failed installation
- Installer thinks Python is already installed

**Solution**:
```
1. Close the dialog (click X, don't select any option)
2. Delete the entire python_embed folder
3. Run start_agent.bat again
4. It will use embeddable Python (avoids this issue)
```

**Prevention in v3.0**:
- Embeddable Python is now the primary method
- Doesn't touch Windows registry
- This issue should rarely occur now

### Issue 2: Download Fails

**Symptoms**:
```
[Error] Failed to download Python
This could be due to:
- Internet connection issues
- Firewall blocking the download
- Antivirus blocking the download
```

**Diagnosis**:
Check `install_verbose.log` for lines like:
```
[Download] Starting download from: https://www.python.org/...
ERROR: <specific error message>
```

**Common causes**:
- **No internet**: Check network connection
- **Firewall**: Allow PowerShell to make HTTPS connections
- **Antivirus**: Temporarily disable or add exception
- **Proxy**: May need to configure PowerShell proxy

**Solution**:
```batch
# Test internet connectivity
powershell -Command "Test-NetConnection www.python.org -Port 443"

# If behind proxy, configure:
powershell -Command "[System.Net.WebRequest]::DefaultWebProxy.Credentials = [System.Net.CredentialCache]::DefaultCredentials"
```

### Issue 3: Extraction Fails

**Symptoms**:
```
[Error] Extraction failed
[Error] python.exe not found after extraction
```

**Diagnosis**:
Check `install_verbose.log` for:
```
[Extract] Starting extraction
ERROR: <extraction error>
```

**Common causes**:
- Corrupted download
- Disk full during extraction
- Antivirus quarantining files
- Permission issues

**Solution**:
1. Delete partial files:
   - Delete `python_embed` folder
   - Delete `python-3.11.9-embed-amd64.zip` if present
2. Free up disk space (need ~50 MB)
3. Temporarily disable antivirus
4. Run from a folder you own (not Program Files)
5. Try again

### Issue 4: Pip Installation Fails

**Symptoms**:
```
[Error] pip is not available
[Error] pip not working
```

**Diagnosis**:
Check `install_verbose.log` for:
```
[Setup] Installing pip
<pip installation errors>
```

**Common causes**:
- get-pip.py download failed
- Python not configured correctly
- Missing dependencies

**Solution**:
```
1. Verify Python works:
   python_embed\python.exe --version

2. Manually install pip:
   - Download get-pip.py from https://bootstrap.pypa.io/get-pip.py
   - Run: python_embed\python.exe get-pip.py

3. Verify pip:
   python_embed\python.exe -m pip --version
```

### Issue 5: Package Installation Fails

**Symptoms**:
```
[Error] Failed to install packages
```

**Diagnosis**:
Check `install_verbose.log` for:
```
[Packages] Installing python-socketio requests
<pip error messages>
```

**Common causes**:
- PyPI connection issues
- Incompatible package versions
- Missing build tools

**Solution**:
```
# Manual installation
python_embed\python.exe -m pip install --upgrade pip
python_embed\python.exe -m pip install python-socketio requests

# If still fails, try one at a time:
python_embed\python.exe -m pip install python-socketio
python_embed\python.exe -m pip install requests

# Check what's installed:
python_embed\python.exe -m pip list
```

## Reading install_verbose.log

### Example of Successful Installation

```
[Diagnostic] Starting installation diagnostics...
Time: 10/22/2025 17:30:45
Working Directory: C:\Users\Username\Agent
Target Directory: C:\Users\Username\Agent\python_embed

[Check] Existing python_embed directory found
[Test] Testing existing python.exe
[OK] Existing Python works, checking packages...
[OK] All packages already installed!
```

### Example of Failed Installation

```
[Download] Starting download from: https://www.python.org/...
ERROR: The remote server returned an error: (403) Forbidden.

[Error] Download failed
[Error] Full installer download failed
```

**This tells you**: Network/firewall is blocking access to python.org

## Testing the Installation

After installation completes, use the verification script:

```
test_installation.bat
```

### What it checks:

1. **Python executable exists**
   ```
   [1/4] Checking Python executable...
   OK: python.exe found
   ```

2. **Python version**
   ```
   [2/4] Testing Python version...
   Python 3.11.9
   OK: Python is working
   ```

3. **Required packages**
   ```
   [3/4] Testing required packages...
   OK: python-socketio installed
   OK: requests installed
   ```

4. **tkinter availability**
   ```
   [4/4] Testing tkinter (GUI support)...
   OK: tkinter available
   ```
   OR
   ```
   WARNING: tkinter not available
   This is normal for embeddable Python installations
   ```

## Manual Recovery Steps

If automatic installation completely fails:

### Option 1: Manual Embeddable Python

```batch
1. Download: https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
2. Extract to: <agent_folder>\python_embed\
3. Edit python_embed\python311._pth:
   - Change "#import site" to "import site" (remove #)
4. Download: https://bootstrap.pypa.io/get-pip.py
5. Run: python_embed\python.exe get-pip.py
6. Run: python_embed\python.exe -m pip install python-socketio requests
7. Test: python_embed\python.exe agent.py
```

### Option 2: Use System Python

```batch
1. Install Python 3.11.9 from python.org (normal installation)
2. Open command prompt in agent folder
3. Create virtual environment:
   python -m venv python_embed
4. Activate: python_embed\Scripts\activate
5. Install packages: pip install python-socketio requests
6. Test: python agent.py
```

## Contacting Support

If you need to contact support, provide:

1. **install_verbose.log** (full diagnostic log)
2. **install_log.txt** (if it exists)
3. Description of:
   - What step failed
   - What error message appeared
   - Your system (Windows version, antivirus, etc.)
   - Whether you're behind a proxy/firewall

## Version History

**v3.0 (2025-10-22)**
- Changed to embeddable Python as primary method
- Added install_verbose.log with detailed diagnostics
- Enhanced error messages with specific troubleshooting
- Improved detection and cleanup of corrupted installations
- Better handling of registry conflicts

**v2.0 (2025-10-21)**
- Added dual installation methods
- Added basic logging

**v1.0 (2025-10-20)**
- Initial release
