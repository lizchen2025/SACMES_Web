# SACMES Agent Deployment Guide

## Package Information

**File**: SACMES_Agent.zip
**Size**: ~90 KB
**Version**: 2.0 (Robust Installation)
**Date**: 2025-10-22

## What's New

### Enhanced Installation Robustness

The new agent package includes a completely rewritten installation system with multiple fallback methods to handle various Python environment conflicts:

#### Method 1: Full Python Installer (Preferred)
- Downloads and installs Python 3.11.9 with full GUI support (tkinter)
- Installs to local directory (no system-wide changes)
- Includes pip for package management

#### Method 2: Embeddable Python (Fallback)
- If full installer fails, automatically falls back to embeddable Python
- Downloads smaller embeddable package
- Configures pip manually
- Note: tkinter not available in this mode, but agent still functions

### Key Features

1. **Conflict Resolution**
   - Temporarily clears PATH during installation to avoid conflicts
   - Detects existing corrupted installations and removes them
   - Verifies installation success before proceeding

2. **Detailed Logging**
   - Creates `install_log.txt` with detailed error information
   - Helps troubleshoot installation failures
   - Provides actionable error messages

3. **Installation Verification**
   - New `test_installation.bat` script to verify setup
   - Tests Python executable, packages, and tkinter
   - Provides clear pass/fail status

4. **User-Friendly Error Messages**
   - Clear explanations of common issues
   - Suggests solutions for antivirus blocks, disk space, etc.
   - Manual installation instructions if automatic methods fail

## Package Contents

```
SACMES_Agent.zip
├── agent.py                  # Agent source code
├── start_agent.bat          # Main launcher (run this)
├── install_python.bat       # Robust first-time setup
├── test_installation.bat    # Installation verification tool
├── Netzlab.ico             # Application icon
└── README.txt              # User documentation
```

## Deployment Steps

### Option 1: Direct Download (Recommended)

1. Upload `SACMES_Agent.zip` to your web server's static files directory
2. Update the download link in your frontend to point to this file
3. Users download and extract the ZIP
4. Users run `start_agent.bat`

### Option 2: GitHub Release

1. Create a new release in your GitHub repository
2. Upload `SACMES_Agent.zip` as a release asset
3. Update frontend download link to GitHub release URL

Example:
```
https://github.com/your-org/your-repo/releases/latest/download/SACMES_Agent.zip
```

## Testing Checklist

Before deploying, test on a clean system:

- [ ] Extract SACMES_Agent.zip
- [ ] Run `start_agent.bat` (should trigger automatic installation)
- [ ] Wait for Python download and installation (~1-2 minutes)
- [ ] Verify agent window opens
- [ ] Run `test_installation.bat` to verify all components
- [ ] Test with antivirus enabled (may require temporary disable)
- [ ] Test on system with existing Python installation
- [ ] Verify tkinter works (GUI should display)

## Common Installation Scenarios

### Scenario 1: Clean System (No Python)
✅ Method 1 succeeds → Full installation with tkinter

### Scenario 2: Antivirus Blocks Installer
⚠️ Method 1 fails → Method 2 succeeds with embeddable Python
📝 User sees clear message about limited GUI support

### Scenario 3: Conflicting Python Installation
✅ Temporary PATH clearing prevents conflicts
✅ Installation to local directory avoids system Python

### Scenario 4: Network Issues During Download
❌ Both methods fail → Clear error with manual installation instructions
📝 User can retry or install Python manually to correct location

## Troubleshooting for Users

All troubleshooting information is included in README.txt within the package.

### Quick Solutions

**Installation fails repeatedly**
1. Delete `python_embed` folder
2. Temporarily disable antivirus
3. Run `start_agent.bat` again
4. Check `install_log.txt` for details

**tkinter not available**
- Normal for embeddable Python (fallback method)
- Agent still works but with limited GUI features
- To get full GUI: delete `python_embed`, disable antivirus, retry

**Agent won't start**
1. Run `test_installation.bat`
2. Check which component is failing
3. Follow suggested solutions in output

## Maintenance

### Updating the Agent

To update `agent.py` only (without changing installation):

1. Modify `agent.py`
2. Run `create_agent_package.ps1` to rebuild ZIP
3. Redeploy ZIP file
4. Users extract and overwrite `agent.py` only

### Updating Python Version

1. Edit `install_python.bat`:
   - Update `PYTHON_VERSION` variable
   - Update URLs for both full installer and embeddable
2. Run `create_agent_package.ps1`
3. Test on clean system
4. Redeploy

## Support

Direct users to:
- README.txt (included in package)
- Check `install_log.txt` for detailed errors
- GitHub issues: https://github.com/lizchen2025/SACMES_Web/issues

## Technical Notes

### Why Two Installation Methods?

1. **Full Installer**: Provides complete Python with tkinter, better user experience
2. **Embeddable**: More reliable, bypasses many system-level installation issues
3. **Automatic Fallback**: Maximizes success rate across diverse environments

### File Paths

- Python installs to: `<agent_folder>\python_embed\`
- No system PATH modifications
- Fully portable - can move folder anywhere
- Complete removal: just delete agent folder

### Security Considerations

- No admin rights required
- No system-wide changes
- All files contained in agent folder
- Source code included for transparency
- Uses official Python distributions only

## Version History

**v2.0 (2025-10-22)**
- Complete rewrite of installation system
- Added dual installation methods with automatic fallback
- Added detailed logging to install_log.txt
- Added test_installation.bat verification tool
- Enhanced error messages and troubleshooting
- PATH conflict resolution
- Corrupted installation detection and recovery

**v1.0 (2025-10-21)**
- Initial release with basic installation
- Single installation method (full installer only)
