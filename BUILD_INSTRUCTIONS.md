# SACMES Agent - Build Instructions

## Overview

This document provides step-by-step instructions for creating the SACMES Agent distribution package from source.

## Prerequisites

- Windows 10 or later (64-bit)
- Internet connection (for downloading Python installer)
- Approximately 500 MB free disk space (temporary)
- PowerShell execution policy allowing script execution

## Build Process

### Step 1: Clean Python 3.11 Registry (Optional)

If you have Python 3.11 installed on your development machine and want to avoid conflicts:

```batch
CLEAN_PYTHON311_REGISTRY.bat
```

Verify the cleanup:

```batch
TEST_REGISTRY_CLEAN.bat
```

Expected output: All registry entries should show "CLEAN" status.

### Step 2: Download Python 3.11.9 Full Installer

```batch
download_python311.bat
```

This downloads `python-3.11.9-amd64.exe` (~30 MB).

Time required: 2-5 minutes depending on connection speed.

### Step 3: Extract tkinter Files

```batch
extract_tkinter_311.bat
```

This script will:
1. Install Python 3.11.9 to a temporary location
2. Extract tkinter library files
3. Extract tcl/tk runtime
4. Extract required DLL files
5. Clean up temporary installation

Output directory: `tkinter_package/` (~50-60 MB)

Time required: 5-10 minutes.

Verify extraction:
- `tkinter_package/Lib/tkinter/` should contain Python files
- `tkinter_package/DLLs/` should contain `_tkinter.pyd`, `tcl86t.dll`, `tk86t.dll`
- `tkinter_package/tcl/` should contain `tcl8.6/` and `tk8.6/` folders

### Step 4: Create Distribution Package

```batch
package_final.bat
```

This creates `SACMES_Agent.zip` containing:
- `agent.py`
- `start_agent.bat`
- `install_portable_python.bat`
- `download_file.ps1`
- `tkinter_package/` (all extracted files)
- `README.md`

Final package size: ~20 MB (compressed)

Time required: 1-2 minutes.

### Step 5: Deploy Package (Optional)

The packaging script will prompt to copy the package to `static/downloads/`.

Manual deployment:
```batch
copy SACMES_Agent.zip static\downloads\SACMES_Agent.zip
```

## File Descriptions

### Build Scripts (Developer Use)

| File | Purpose |
|------|---------|
| `CLEAN_PYTHON311_REGISTRY.bat` | Remove Python 3.11 registry entries |
| `TEST_REGISTRY_CLEAN.bat` | Verify registry cleanup |
| `download_python311.bat` | Download Python 3.11.9 installer |
| `extract_tkinter_311.bat` | Extract tkinter from installer |
| `package_final.bat` | Create distribution package |

### Distribution Files (End User)

| File | Purpose |
|------|---------|
| `agent.py` | Main agent application |
| `start_agent.bat` | User-facing launcher |
| `install_portable_python.bat` | Portable Python installer |
| `download_file.ps1` | Download utility |
| `tkinter_package/` | Pre-extracted tkinter library |
| `README.md` | User documentation |

## Troubleshooting Build Issues

### Issue: extract_tkinter_311.bat fails with "Installation failed"

**Cause:** Python installer requires administrator privileges or is blocked by antivirus.

**Solution:**
1. Run `extract_tkinter_311.bat` as Administrator
2. Temporarily disable antivirus
3. Ensure temp directory is not read-only

### Issue: tkinter extraction incomplete

**Cause:** Installation timeout too short or disk space insufficient.

**Solution:**
1. Increase timeout in `extract_tkinter_311.bat` (line with `timeout /t 20`)
2. Verify at least 500 MB free disk space
3. Check that Python installer is not corrupted (re-download if needed)

### Issue: Package creation fails

**Cause:** Missing required files.

**Solution:**
Run verification before packaging:
```batch
dir agent.py
dir start_agent.bat
dir install_portable_python.bat
dir download_file.ps1
dir tkinter_package\Lib\tkinter
```

All files must exist.

### Issue: Registry cleanup warnings

**Cause:** Insufficient permissions to modify HKEY_LOCAL_MACHINE.

**Solution:**
Run `CLEAN_PYTHON311_REGISTRY.bat` as Administrator, or ignore HKLM warnings (HKCU cleanup is usually sufficient).

## Version Compatibility

### Python Version Requirements

- **Critical:** Embeddable Python and tkinter extraction must use the **same version**
- Current configuration: Python 3.11.9
- To change version: Update `PYTHON_VERSION` variable in all scripts

### Changing Python Version

If you need to use a different Python version:

1. Update `download_python311.bat`:
   ```batch
   set PYTHON_VERSION=3.11.x
   ```

2. Update `extract_tkinter_311.bat`:
   ```batch
   set PYTHON_VERSION=3.11.x
   ```

3. Update `install_portable_python.bat`:
   ```batch
   set PYTHON_VERSION=3.11.x
   ```

4. Rebuild package using updated scripts

**Warning:** Mixing Python versions will cause "DLL load failed" errors.

## Testing the Build

### Test Extraction

After running `extract_tkinter_311.bat`, verify files:

```batch
dir tkinter_package\Lib\tkinter
dir tkinter_package\DLLs
dir tkinter_package\tcl
```

### Test Package

1. Extract `SACMES_Agent.zip` to a test folder
2. Run `start_agent.bat`
3. Verify portable Python installs successfully
4. Verify agent launches without errors

### Clean Test Environment

For clean testing, use a virtual machine or different computer that:
- Does not have Python installed
- Does not have development tools
- Represents typical end-user environment

## Maintenance

### Regular Updates

Update the package when:
- Python 3.11.x security updates are released
- Agent.py receives updates
- Dependencies (socketio, requests) require updates

### Rebuild Process

For routine updates:
1. Update `agent.py` source file
2. Run `package_final.bat` (skip extraction if tkinter unchanged)
3. Test package in clean environment
4. Deploy to `static/downloads/`

For Python version updates:
1. Run full build process (all steps)
2. Extensive testing required
3. Update version numbers in README.md

## Package Size Optimization

Current sizes:
- Python 3.11.9 embeddable: ~10 MB download
- tkinter_package: ~50-60 MB extracted, ~10 MB compressed
- Total package: ~20 MB
- Total installed: ~80-100 MB

Optimization is generally not recommended as it may break tkinter functionality.

## Distribution

The final package (`SACMES_Agent.zip`) can be distributed via:
- Web download (recommended: place in `static/downloads/`)
- Email attachment (if size permits)
- Network share
- USB drive

## Security Considerations

- The package downloads Python from official python.org servers
- All downloads use HTTPS
- No code signing is implemented (consider adding for enterprise deployment)
- Package should be distributed via trusted channels only

## Support

For build issues or questions:
1. Review this document
2. Check troubleshooting section
3. Verify all prerequisites are met
4. Contact development team if issues persist
