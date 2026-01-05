# SACMES Local - Troubleshooting Guide

**Last Updated:** 2026-01-05

## Overview

This guide provides comprehensive troubleshooting steps for diagnosing and resolving common issues with the SACMES Local application, particularly focusing on file reading and processing problems.

## Quick Diagnostic Tools

### 1. Built-in Diagnostics Panel

The application now includes a comprehensive diagnostics panel accessible from the main interface.

**How to Access:**
1. Open the application in your browser (http://localhost:5000)
2. Click the "Diagnostics" button in the top navigation bar
3. The diagnostics panel will open as an overlay

**Features:**
- System status check (Python version, working directory, platform)
- Analyzer module loading verification
- Folder monitoring status
- File access testing
- Manual file processing trigger
- Real-time activity log
- Common issues reference

### 2. Log Files

All debug information is now logged to:
- **Console Output:** Real-time logs in the terminal where the server is running
- **Log File:** `sacmes_local_debug.log` in the application root directory

**Log Levels:**
- DEBUG: Detailed information for troubleshooting
- INFO: General operational messages
- WARNING: Potential issues that don't prevent operation
- ERROR: Serious problems that prevent functionality

## Common Issues and Solutions

### Issue 1: Files Not Being Detected

**Symptoms:**
- File list remains empty after starting monitoring
- New files added to folder don't appear
- No activity in the log

**Diagnostic Steps:**

1. **Run System Diagnostics:**
   - Open Diagnostics panel
   - Enter your folder path in "Run Diagnostics" section
   - Click "Run Diagnostics"
   - Check results for:
     - Path exists: Should be "Yes"
     - Is Directory: Should be "Yes"
     - Can Read Directory: Should be "Yes"
     - File Count: Should show number of files
     - Can Read Files: Should be "Yes"

2. **Check Folder Path:**
   - Verify path is absolute (e.g., `e:\SACMES_Web_Local\test_data`)
   - Check for typos or invalid characters
   - Ensure folder exists before starting monitoring
   - On Windows, use backslashes or forward slashes (both work)

3. **Verify File Extensions:**
   - Only `.txt`, `.dta`, `.csv` files are detected
   - File extension must be lowercase or uppercase (both work)
   - Hidden files (starting with `.`) are ignored

4. **Check Monitoring Status:**
   - Status should show "Monitoring: [your_path]"
   - "Stop" button should be enabled
   - If not, click "Start Monitoring" again

5. **Check Server Logs:**
   - Look for "Found X existing files in folder" message
   - Check for permission errors
   - Look for file reading errors

**Solutions:**

- **Incorrect Path:**
  ```
  Correct: e:\SACMES_Web_Local\test_data
  Correct: e:/SACMES_Web_Local/test_data
  Incorrect: \test_data (relative path)
  Incorrect: e:\SACMES_Web_Local\test_data\ (trailing slash may cause issues on some systems)
  ```

- **Permission Issues:**
  - Ensure the folder has read permissions
  - Try running the application with appropriate permissions
  - Check if antivirus is blocking access

- **Files Not Showing:**
  - Refresh the browser (Ctrl + Shift + R)
  - Stop and restart monitoring
  - Check if files have correct extensions
  - Use "Test File Read" in diagnostics panel to verify specific file

### Issue 2: Files Not Being Processed

**Symptoms:**
- Files appear in the list but no analysis happens
- No charts or results displayed
- No errors shown

**Diagnostic Steps:**

1. **Check Analysis Session:**
   - Have you clicked "Start Analysis" button?
   - Are analysis parameters filled in correctly?
   - Check browser console for "analysis_session_started" event

2. **Verify Filename Format:**
   - For SWV: Filename must contain frequency (e.g., `SWV_15Hz.txt`)
   - Pattern: `_[number]Hz` (case insensitive)
   - Examples: `SWV_15Hz.txt`, `data_200hz.dta`, `test-1000Hz.csv`

3. **Test Manual Processing:**
   - Open Diagnostics panel
   - Go to "Manual File Processing" section
   - Enter folder path and filename
   - Select analysis type (SWV/CV)
   - Click "Process"
   - Check results for errors

4. **Check File Content:**
   - Use "Test File Read" in diagnostics panel
   - Verify file contains valid data
   - Check "First 100 chars" output for expected format
   - Ensure file is not empty

**Solutions:**

- **No Analysis Session:**
  1. Fill in all required parameters (electrodes, baseline, etc.)
  2. Click "Start Analysis" button
  3. Status should show analysis is active
  4. Then start folder monitoring

- **Invalid Filename:**
  ```
  Valid: SWV_15Hz.txt, data_200Hz.dta, test-60hz.csv
  Invalid: SWV_15.txt (missing Hz), SWV.txt (no frequency)
  ```

- **Invalid File Content:**
  - File must have header: `Potential/V, Current/A` (or similar)
  - Data should be comma or tab separated
  - Numbers should be in scientific notation or decimal
  - Check sample files in test_data folder for format reference

- **Safety Check Failed:**
  - File size must be under limit
  - File must not contain suspicious patterns
  - Check diagnostics panel for specific safety error

### Issue 3: Frequency Scan Not Working

**Symptoms:**
- Click "Scan Folder" but no frequencies appear
- Frequency checkboxes remain empty
- Error message or no response

**Diagnostic Steps:**

1. **Check Prerequisites:**
   - Is folder path entered?
   - Are you in "Frequency Map" mode (not "Continuous Monitor")?
   - Is "Scan Folder" button clickable?

2. **Verify File Naming:**
   - Files must contain frequency with Hz
   - Format: `[prefix]_[number]Hz[.extension]`
   - Use diagnostics panel to test file read and check "Frequency Detected" field

3. **Check Browser Console:**
   - Open browser DevTools (F12)
   - Check Console tab for errors
   - Look for "scan_available_frequencies" events
   - Check Network tab for WebSocket messages

**Solutions:**

- **No Folder Path:**
  - Enter folder path first
  - Path must be valid and accessible
  - Then click "Scan Folder"

- **No Matching Files:**
  - Ensure files contain frequency in filename
  - File handle (prefix) is optional but filters results
  - Examples of valid filenames:
    ```
    SWV_15Hz.txt (frequency: 15)
    SWV_200Hz.txt (frequency: 200)
    data_1000hz.csv (frequency: 1000)
    test-60Hz.dta (frequency: 60)
    ```

- **Wrong Mode:**
  - Select "Frequency Map" from analysis mode dropdown
  - Scan folder option only appears in this mode
  - Continuous monitor doesn't need frequency scanning

### Issue 4: Connection or Socket Issues

**Symptoms:**
- "Disconnected" status in diagnostics panel
- No real-time updates
- Actions don't trigger responses

**Diagnostic Steps:**

1. **Check Server:**
   - Is the server running? (check terminal window)
   - Look for "Running on http://..." message
   - Check for error messages in server terminal

2. **Check Browser Connection:**
   - Open Diagnostics panel
   - Check "Connection Status" section
   - Should show "Connected" in green

3. **Check Network:**
   - Can you access http://localhost:5000 in browser?
   - Is firewall blocking the connection?
   - Try different browser

**Solutions:**

- **Server Not Running:**
  ```batch
  # Windows
  start.bat

  # Or manually
  python app_local.py
  ```

- **Connection Failed:**
  - Refresh browser page (F5)
  - Clear browser cache (Ctrl + Shift + Del)
  - Try different port if 5000 is in use
  - Check firewall settings

- **Socket Disconnected:**
  - Refresh the page
  - Check server logs for errors
  - Restart the server

### Issue 5: Analysis Results Not Displaying

**Symptoms:**
- Files are processed (logs show success)
- No charts appear
- No data in results section

**Diagnostic Steps:**

1. **Check Analysis Module:**
   - Open Diagnostics panel
   - Run diagnostics
   - Verify "SWV Analyzer: Loaded" or "CV Analyzer: Loaded"

2. **Check Browser Console:**
   - Open DevTools (F12)
   - Look for JavaScript errors
   - Check for chart rendering errors

3. **Verify Data Format:**
   - Use manual file processing to test single file
   - Check server logs for processing errors
   - Verify file content format matches expected

**Solutions:**

- **Analyzer Not Loaded:**
  - Check that `data_processing` folder exists
  - Verify analyzer modules are present
  - Check server startup logs for import errors
  - Ensure required Python packages are installed

- **Chart Not Rendering:**
  - Check browser console for errors
  - Verify Chart.js is loaded
  - Try refreshing the page
  - Check if results data structure is correct

- **Data Processing Error:**
  - Check server logs for detailed error
  - Verify file format matches expected structure
  - Try with known good sample file
  - Check analysis parameters are valid

## Advanced Troubleshooting

### Debug Mode

The application now runs in DEBUG mode by default, providing verbose logging.

**To enable even more detailed logging:**

1. Edit `app_local.py`:
   ```python
   logger.setLevel(logging.DEBUG)  # Already enabled
   ```

2. Check `sacmes_local_debug.log` for detailed trace

### Manual File Processing

Use the diagnostics panel to manually process files:

1. Start an analysis session first (important!)
2. Open Diagnostics panel
3. Enter folder path and filename
4. Select analysis type
5. Click "Process"
6. Watch server logs for detailed processing steps

### Testing Individual Components

**Test File Reading:**
```python
# In diagnostics panel, use "Test File Read"
# This will show:
# - File exists
# - File is readable
# - File size
# - File content preview
# - Safety check results
# - Frequency detection
```

**Test Folder Access:**
```python
# In diagnostics panel, use "Run Diagnostics" with folder path
# This will test:
# - Folder exists
# - Folder is readable
# - Can list files
# - Can read file content
```

## Diagnostic Checklist

Use this checklist when troubleshooting file reading issues:

- [ ] Server is running (check terminal)
- [ ] Browser shows "Connected" in diagnostics panel
- [ ] Folder path is absolute and correct
- [ ] Folder exists and is accessible
- [ ] Folder contains .txt, .dta, or .csv files
- [ ] Files have frequency in filename (for SWV: _15Hz, _200Hz, etc.)
- [ ] Analysis session is started (clicked "Start Analysis")
- [ ] Analysis parameters are filled in
- [ ] Monitoring is started (status shows "Monitoring: ...")
- [ ] File list appears after starting monitoring
- [ ] No errors in browser console (F12)
- [ ] No errors in server logs
- [ ] Analyzers loaded successfully (check diagnostics)
- [ ] Test file read works in diagnostics panel

## Getting Help

If issues persist after trying these steps:

1. **Collect Information:**
   - Run full diagnostics (save results)
   - Copy recent server logs (from `sacmes_local_debug.log`)
   - Copy browser console errors (F12 → Console)
   - Note exact steps to reproduce issue

2. **Check Logs:**
   - Server log: `sacmes_local_debug.log`
   - Browser console: F12 → Console tab
   - Diagnostics panel: Activity Log section

3. **Test with Sample Data:**
   - Use provided test files in `test_data/` folder
   - If sample data works, issue is with your data format
   - If sample data fails, issue is with setup

## Log File Analysis

### Understanding Log Messages

**Normal Operation:**
```
INFO - Client connected: sid=...
INFO - Started folder monitoring: path
INFO - Found 5 existing files in folder
INFO - File detected and validated: SWV_15Hz.txt - sending for processing
INFO - Received file: SWV_15Hz.txt (1234 bytes)
INFO - Processing in CONTINUOUS mode: SWV_15Hz.txt
INFO - File processed successfully: SWV_15Hz.txt
```

**Common Error Patterns:**

```
ERROR - Error starting folder monitor: [Errno 2] No such file or directory
  Solution: Check folder path is correct

WARNING - File SWV_15.txt does not match expected pattern
  Solution: Add frequency to filename (SWV_15Hz.txt)

ERROR - File not readable: SWV_15Hz.txt
  Solution: Check file permissions

WARNING - No analysis parameters set
  Solution: Start analysis session first

ERROR - Safety check failed: File too large
  Solution: Check file size is reasonable
```

### Enabling Different Log Levels

In `app_local.py`:
```python
# DEBUG: Very detailed
logger.setLevel(logging.DEBUG)

# INFO: Normal operation (default)
logger.setLevel(logging.INFO)

# WARNING: Only warnings and errors
logger.setLevel(logging.WARNING)
```

## Performance Tips

1. **Large Folders:**
   - If folder has many files, initial scan may take time
   - Consider using file handle filter to limit scope

2. **File Size:**
   - Large files may take longer to process
   - Watch server logs for processing progress

3. **Multiple Files:**
   - Files are processed concurrently
   - Check activity log to see processing queue

## Summary

The new troubleshooting mechanisms provide:

1. **Built-in Diagnostics Panel** - Interactive testing and debugging
2. **Enhanced Logging** - Detailed debug information in logs and console
3. **Manual Processing** - Test individual files on demand
4. **File Read Testing** - Verify file accessibility and format
5. **System Diagnostics** - Check all components status
6. **Activity Log** - Real-time event monitoring

Use these tools to quickly identify and resolve file reading and processing issues.
