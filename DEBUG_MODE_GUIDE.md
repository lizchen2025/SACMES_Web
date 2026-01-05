# Running SACMES Local in Debug Mode

## Quick Start - See Full Terminal Output

Instead of using `start.bat`, use the new debug runner to see all errors:

```batch
run_debug.bat
```

This will:
- Show all debug messages in terminal
- Display full error traces
- Not auto-open browser
- Keep terminal window visible

## Alternative: Run Python Directly

You can run the application directly with Python:

```batch
python app_local.py
```

Or if you need to specify Python path:

```batch
"C:\path\to\python.exe" app_local.py
```

## Browser Cache Issues - IMPORTANT

When code changes don't appear, the browser is caching old JavaScript files.

### Solution 1: Hard Refresh (Recommended)

After starting the server, hard refresh your browser:

**Windows/Linux:**
- Chrome/Edge: `Ctrl + Shift + R`
- Firefox: `Ctrl + Shift + R`
- Or: `Ctrl + F5`

**Mac:**
- Chrome/Safari: `Cmd + Shift + R`
- Or: `Cmd + Option + R`

### Solution 2: Clear Browser Cache

1. Open browser DevTools: `F12`
2. Right-click on refresh button
3. Select "Empty Cache and Hard Reload"

### Solution 3: Disable Cache in DevTools

1. Open DevTools: `F12`
2. Go to Network tab
3. Check "Disable cache" checkbox
4. Keep DevTools open while working

## Cache Control Added

The application now includes cache-busting headers to prevent JavaScript caching:

```python
# In app_local.py
@app.after_request
def add_cache_control(response):
    if request.path.endswith(('.js', '.css', '.html')):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response
```

This means new code should load immediately, but you may still need to hard refresh once.

## Recommended Development Workflow

1. **Start server in debug mode:**
   ```batch
   run_debug.bat
   ```

2. **Open browser with DevTools:**
   - Press `F12` to open DevTools
   - Go to Network tab
   - Check "Disable cache"

3. **Navigate to application:**
   - Go to http://localhost:5000
   - Do hard refresh: `Ctrl + Shift + R`

4. **Monitor both consoles:**
   - Server terminal: See backend logs
   - Browser console: See frontend logs

5. **After code changes:**
   - Server restarts automatically (if using watchdog) OR restart manually
   - Browser: Hard refresh `Ctrl + Shift + R`
   - Check both consoles for errors

## Checking If Updates Loaded

### Method 1: Check Browser Console

1. Open browser console: `F12` → Console tab
2. You should see initialization messages:
   ```
   Initializing SACMES Local Application...
   SACMES Local Application initialized successfully
   ```

3. Check for your new code:
   - Look for new console.log messages
   - Check for new diagnostic features
   - Verify DiagnosticsPanel exists: `window.diagnosticsPanel`

### Method 2: Check Source Files

1. Open DevTools: `F12`
2. Go to Sources tab
3. Navigate to your JS files (e.g., `diagnostics_panel.js`)
4. Check if code matches your latest changes
5. If old code shown: Hard refresh needed

### Method 3: Test New Features

1. Look for "Diagnostics" button in navigation
2. If not visible: Code not loaded, hard refresh needed
3. Click Diagnostics button
4. Panel should open with new features

## Common Issues

### Issue: Changes Don't Appear

**Symptom:** Code changes not visible in browser

**Solutions:**
1. Hard refresh: `Ctrl + Shift + R`
2. Clear cache completely
3. Close and reopen browser
4. Try incognito/private window
5. Check browser console for JavaScript errors

### Issue: Old Error Messages

**Symptom:** Still seeing old JavaScript errors that should be fixed

**Solutions:**
1. Verify server restarted with new code
2. Check file modification time in file explorer
3. Hard refresh browser
4. Check Sources tab in DevTools to verify file content

### Issue: Server Not Restarting

**Symptom:** Code changes in Python files not taking effect

**Solutions:**
1. Stop server: `Ctrl + C`
2. Restart: `run_debug.bat` or `python app_local.py`
3. Verify terminal shows latest code (check log messages)

### Issue: Multiple Instances Running

**Symptom:** Port 5000 already in use

**Solutions:**
1. Check Task Manager for multiple Python processes
2. Kill all Python processes
3. Restart server
4. Or: Use different port (server will auto-select)

## Debugging Tips

### 1. Use Browser Console

Always keep browser console open:
- Press `F12`
- Monitor Console tab for errors
- Check Network tab for failed requests
- Watch for WebSocket connection status

### 2. Monitor Server Terminal

Watch server terminal for:
- File detection messages
- Processing errors
- Socket connection events
- Detailed error traces

### 3. Use Diagnostics Panel

New built-in diagnostics:
1. Click "Diagnostics" button
2. Run system diagnostics
3. Test file reading
4. Monitor activity log
5. Check for specific errors

### 4. Check Log File

Review `sacmes_local_debug.log`:
- Contains all debug messages
- Persistent record of events
- Helpful for reviewing past issues

### 5. Test in Stages

1. Test backend first (check server logs)
2. Test connection (check socket status in diagnostics)
3. Test file reading (use test file read tool)
4. Test processing (use manual process feature)

## Verifying Latest Code Loaded

Run this checklist to verify you have latest code:

**Backend (Server):**
- [ ] Stopped old server process
- [ ] Started with `run_debug.bat` or `python app_local.py`
- [ ] See "SACMES LOCAL APPLICATION INITIALIZED" in terminal
- [ ] See cache control headers being added (check logs)
- [ ] No import errors or warnings

**Frontend (Browser):**
- [ ] Hard refreshed browser: `Ctrl + Shift + R`
- [ ] DevTools open with cache disabled
- [ ] See "SACMES Local Application initialized successfully" in console
- [ ] See "Diagnostics" button in navigation
- [ ] Can open diagnostics panel
- [ ] No JavaScript errors in console

## Quick Test - Verify Diagnostics Loaded

Run this in browser console:

```javascript
// Check if DiagnosticsPanel loaded
console.log('DiagnosticsPanel exists:', typeof DiagnosticsPanel);

// Check if diagnostics button exists
console.log('Diagnostics button exists:',
    document.getElementById('showDiagnosticsBtn') !== null);

// Try to open diagnostics
if (window.diagnosticsPanel) {
    console.log('DiagnosticsPanel instance found');
} else {
    console.log('DiagnosticsPanel not initialized - hard refresh needed');
}
```

## File Modification Times

Check when files were last modified:

**Windows:**
```batch
dir /T:W app_local.py
dir /T:W static\js\diagnostics_panel.js
dir /T:W static\js\main_local.js
```

Compare timestamps with when you made changes.

## Using Git to Verify Changes

Check what version you have:

```batch
git log -1 --oneline
git status
```

If behind remote:
```batch
git pull origin local-ui-improvements
```

## Port Conflicts

If port 5000 is busy, the server will auto-select another port.
Check server terminal for actual port:

```
Running on http://localhost:5000
```

Or:
```
Port 5000 is busy, trying 5001...
Running on http://localhost:5001
```

Make sure browser is accessing correct port.

## Summary

**Best practice for development:**

1. Use `run_debug.bat` to see full output
2. Keep browser DevTools open with cache disabled
3. Always hard refresh after code changes: `Ctrl + Shift + R`
4. Monitor both server terminal and browser console
5. Use diagnostics panel to test features
6. Check `sacmes_local_debug.log` for detailed traces

**Every time you modify code:**

1. Save file
2. Restart server (Ctrl+C, then `run_debug.bat`)
3. Hard refresh browser (`Ctrl + Shift + R`)
4. Check both consoles for errors
5. Test your changes

This ensures you always see the latest code and can debug issues effectively.
