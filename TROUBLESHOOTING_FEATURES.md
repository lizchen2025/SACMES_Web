# SACMES Local - Troubleshooting Features Quick Reference

## Overview

The application now includes comprehensive troubleshooting mechanisms to help diagnose and resolve file reading and processing issues.

## Quick Start

### 1. Access the Diagnostics Panel

1. Start the application: Run `start.bat`
2. Open browser: Navigate to http://localhost:5000
3. Click the **"Diagnostics"** button in the top navigation bar
4. The diagnostics panel will open

### 2. Run System Diagnostics

**Purpose:** Check if the system is working correctly

**Steps:**
1. In the diagnostics panel, find "Run Diagnostics" section
2. (Optional) Enter a folder path to test
3. Click **"Run Diagnostics"** button
4. Review results:
   - System information (Python version, working directory)
   - Analyzer status (SWV/CV analyzers loaded)
   - Folder monitoring status
   - File access test results (if path provided)

**What to look for:**
- Analyzers should show "Loaded"
- If folder path provided, should show "Can Read Directory: Yes"
- File count should match number of files in folder

### 3. Test File Reading

**Purpose:** Verify a specific file can be read and is in correct format

**Steps:**
1. In diagnostics panel, find "Test File Reading" section
2. Enter folder path (e.g., `e:\SACMES_Web_Local\test_data`)
3. Enter filename (e.g., `SWV_15Hz.txt`)
4. Click **"Test Read"** button
5. Review results:
   - File exists and is readable
   - File size and line count
   - Safety check status
   - Frequency detected from filename
   - First 100 characters of file content

**What to look for:**
- "Exists: Yes", "Readable: Yes"
- "Safety Check: Passed"
- "Frequency Detected" should show number (for SWV files)
- Content preview should match expected format

### 4. Manual File Processing

**Purpose:** Manually trigger processing of a specific file for testing

**Important:** Start an analysis session FIRST before using this feature

**Steps:**
1. Go to your analysis screen (SWV/CV/HT)
2. Fill in analysis parameters
3. Click **"Start Analysis"** button
4. Open Diagnostics panel
5. In "Manual File Processing" section:
   - Enter folder path
   - Enter filename
   - Select analysis type (SWV/CV)
6. Click **"Process"** button
7. Watch server logs and browser console for processing

**What to look for:**
- Should show "File sent for processing"
- Check Activity Log for file processing events
- Check server console for detailed processing steps
- Results should appear in analysis screen

### 5. Monitor Activity Log

**Purpose:** See real-time events and errors

**Location:** Bottom of diagnostics panel, "Recent Activity Log" section

**What it shows:**
- Connection status changes
- Monitoring start/stop events
- Files detected
- Errors (shown in red)
- Diagnostic results

**Tips:**
- Log auto-scrolls to show latest events
- Red text indicates errors
- Keep panel open while testing to see live updates

## Common Workflows

### Workflow 1: "Files not being detected"

1. Open Diagnostics panel
2. Run diagnostics with your folder path
3. Check results:
   - Path exists? If No → check path is correct
   - Can read directory? If No → check permissions
   - File count shows 0? → check files have correct extensions
4. If results OK, test reading a specific file:
   - Use "Test File Read" with one of your files
   - Check if file is readable and has correct format
5. Check Activity Log for errors

### Workflow 2: "Files detected but not processing"

1. Go to analysis screen (e.g., SWV Analysis)
2. Fill in all parameters
3. Click "Start Analysis" - IMPORTANT
4. Start monitoring your folder
5. Open Diagnostics panel
6. Try manual file processing:
   - Enter folder path and filename
   - Click "Process"
   - Check results for errors
7. If error mentions "No analysis parameters":
   - You forgot to start analysis session
   - Go back to step 2

### Workflow 3: "Frequency scan not working"

1. Test file reading first:
   - Use "Test File Read" in diagnostics
   - Check "Frequency Detected" field
   - Should show a number (e.g., "15")
2. If no frequency detected:
   - Filename must contain "_15Hz" or similar
   - Examples: `SWV_15Hz.txt`, `data_200hz.csv`
3. If frequency detected but scan still fails:
   - Check Activity Log for errors
   - Verify you're in "Frequency Map" mode
   - Ensure folder path is entered

## Log Files

### Console Log (Real-time)

**Location:** Terminal/command prompt where server is running

**Shows:**
- All DEBUG, INFO, WARNING, ERROR messages
- File detection events
- Processing steps
- Detailed error traces

### Debug Log File (Persistent)

**Location:** `sacmes_local_debug.log` in application root

**Shows:**
- Same as console but saved to file
- Useful for reviewing past events
- Can be opened in text editor

**How to use:**
1. Open file in text editor
2. Search for ERROR or WARNING
3. Look at timestamp to find relevant events
4. Check surrounding messages for context

## Diagnostic Events Reference

### run_diagnostics

**Input:**
- folder_path (optional): Path to test

**Output:**
- System information
- Analyzer status
- Monitoring status
- File access test results

**When to use:**
- Initial setup verification
- Checking if system is working
- Testing folder accessibility

### test_file_read

**Input:**
- folder_path: Folder containing file
- filename: Name of file to test

**Output:**
- File existence and accessibility
- File size and line count
- Safety check results
- Frequency detection
- Content preview

**When to use:**
- Verifying specific file is readable
- Checking file format
- Debugging file detection issues

### manual_process_file

**Input:**
- folder_path: Folder containing file
- filename: Name of file to process
- analysis_type: "swv" or "cv"

**Output:**
- Processing status
- Error messages if any

**When to use:**
- Testing file processing
- Debugging analysis issues
- Bypassing automatic detection

**Requirements:**
- Analysis session must be started first
- File must be in correct format
- Analysis parameters must be set

## Tips and Best Practices

1. **Always start diagnostics by running system check**
   - Verifies basic functionality
   - Shows if analyzers are loaded
   - Quick health check

2. **Use test file read before processing**
   - Confirms file is accessible
   - Shows what data looks like
   - Validates filename format

3. **Keep diagnostics panel open while working**
   - See real-time events in Activity Log
   - Quickly spot errors as they happen
   - Monitor file detection

4. **Check both browser and server logs**
   - Browser console: Frontend issues
   - Server logs: Backend processing
   - Together give complete picture

5. **Test with sample files first**
   - Use provided test_data files
   - Confirms system is working
   - Isolates issue to your data vs system

6. **Start simple, add complexity**
   - Test single file first
   - Then try folder monitoring
   - Then try multiple files

## Example Session

**Scenario:** Setting up SWV analysis for the first time

1. Start server: `start.bat`
2. Open browser: http://localhost:5000
3. Click "Diagnostics" button
4. Run diagnostics:
   - Enter: `e:\SACMES_Web_Local\test_data`
   - Click "Run Diagnostics"
   - Verify: Analyzers loaded, can read directory
5. Test file read:
   - Folder: `e:\SACMES_Web_Local\test_data`
   - File: `SWV_15Hz.txt`
   - Click "Test Read"
   - Verify: File readable, frequency detected: 15
6. Close diagnostics panel
7. Go to "SWV Analysis" screen
8. Fill in parameters (electrodes, baseline, etc.)
9. Click "Start Analysis"
10. Enter folder path: `e:\SACMES_Web_Local\test_data`
11. Click "Start Monitoring"
12. Verify: File list appears
13. Open diagnostics to monitor activity
14. Copy a new file to test_data folder
15. Watch Activity Log for "New file detected" message
16. See results appear in analysis screen

## Summary

The troubleshooting features provide:

- **Interactive diagnostics panel** - Point-and-click testing
- **System health checks** - Verify all components working
- **File testing tools** - Test individual files
- **Manual processing** - Bypass automation for testing
- **Real-time monitoring** - See events as they happen
- **Detailed logging** - Debug information for issues
- **Reference guide** - Common problems and solutions

Use these tools to quickly identify and resolve any file reading or processing issues.
