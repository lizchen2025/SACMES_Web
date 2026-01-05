# How to Run SACMES Local - Quick Guide

## Option 1: Debug Mode (Recommended for Development)

Use this to see all terminal errors and debug messages.

### Step 1: Run the debug script

```batch
run_debug.bat
```

### Step 2: Open browser manually

Navigate to: **http://localhost:5000**

### Step 3: Hard refresh browser

**IMPORTANT:** After opening, do a hard refresh to load latest code:

- Press: `Ctrl + Shift + R`
- Or: `Ctrl + F5`

You should now see the latest version.

## Option 2: Direct Python Execution

If you prefer running Python directly:

```batch
python app_local.py
```

Then:
1. Open browser: http://localhost:5000
2. Hard refresh: `Ctrl + Shift + R`

## Option 3: Normal Mode (Auto Browser)

Use the standard launcher:

```batch
start.bat
```

This will:
- Check dependencies
- Auto-open browser
- But may hide some error messages

Still do hard refresh after opening: `Ctrl + Shift + R`

## When Code Doesn't Update

If you modified code but don't see changes:

### 1. Check Server Restarted

- Stop server: Press `Ctrl + C` in terminal
- Start again: `run_debug.bat`
- Wait for "Running on http://localhost:5000" message

### 2. Hard Refresh Browser

- Press: `Ctrl + Shift + R` (Windows/Linux)
- Or: `Cmd + Shift + R` (Mac)

### 3. Clear Browser Cache Completely

In Chrome/Edge:
1. Press `F12` to open DevTools
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### 4. Disable Cache During Development

In browser DevTools:
1. Press `F12`
2. Go to Network tab
3. Check "Disable cache"
4. Keep DevTools open while working

## Verifying Latest Code Loaded

### Check 1: Diagnostics Button

After loading the page, you should see a "Diagnostics" button in the navigation bar.

If you don't see it:
- Hard refresh: `Ctrl + Shift + R`
- Clear cache and try again

### Check 2: Browser Console

1. Press `F12` to open DevTools
2. Go to Console tab
3. You should see:
   ```
   Initializing SACMES Local Application...
   SACMES Local Application initialized successfully
   ```

4. No JavaScript errors should appear

### Check 3: Server Terminal

In the terminal where server is running, you should see:
```
SACMES LOCAL APPLICATION INITIALIZED
Running on http://localhost:5000
```

No errors should appear.

## Recommended Development Setup

### Terminal Window:
```
E:\SACMES_Web_Local> run_debug.bat

============================================
SACMES Local Application - Debug Mode
============================================
Starting application with: python
============================================
Application will start on http://localhost:5000
============================================

INFO - SACMES LOCAL APPLICATION INITIALIZED
INFO - Running on http://localhost:5000
```

### Browser:
1. Open: http://localhost:5000
2. Press `F12` for DevTools
3. Go to Network tab
4. Check "Disable cache"
5. Hard refresh: `Ctrl + Shift + R`

### Now you can:
- See all errors in terminal
- See JavaScript errors in browser console
- Changes load immediately (after hard refresh)
- Full debugging capability

## Testing New Features

After loading latest code:

1. Click "Diagnostics" button (top navigation)
2. Diagnostics panel should open
3. Try "Run Diagnostics" feature
4. Check Activity Log

If diagnostics panel doesn't work:
- Check browser console for errors
- Verify hard refresh was done
- Check server terminal for Python errors

## Common Port Issues

If you see "Port 5000 already in use":

### Option 1: Kill existing process
1. Open Task Manager (Ctrl + Shift + Esc)
2. Find "Python" processes
3. End them
4. Restart server

### Option 2: Use different port
The server will automatically try ports 5001, 5002, etc.
Check terminal output for actual port:
```
Port 5000 is busy, trying 5001...
Running on http://localhost:5001
```

Then open: http://localhost:5001

## Troubleshooting Checklist

Before asking for help, verify:

- [ ] Server is running (check terminal)
- [ ] No errors in server terminal
- [ ] Browser opened correct URL (http://localhost:5000)
- [ ] Hard refreshed browser (`Ctrl + Shift + R`)
- [ ] Browser console shows no errors (F12 → Console)
- [ ] DevTools cache is disabled (F12 → Network → Disable cache)
- [ ] Latest code is in working directory (check file modification times)

## Quick Commands Reference

**Start server (debug mode):**
```batch
run_debug.bat
```

**Start server (normal mode):**
```batch
start.bat
```

**Run with Python directly:**
```batch
python app_local.py
```

**Stop server:**
```
Ctrl + C (in terminal)
```

**Hard refresh browser:**
```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

**Open browser DevTools:**
```
F12 or Ctrl + Shift + I
```

**Check running Python processes:**
```batch
tasklist | findstr python
```

**Kill Python processes:**
```batch
taskkill /F /IM python.exe
```

## Summary

For best development experience:

1. Use `run_debug.bat` to run server
2. Open browser manually to http://localhost:5000
3. Open DevTools (`F12`) and disable cache
4. Hard refresh (`Ctrl + Shift + R`) to load code
5. Monitor both server terminal and browser console
6. After any code change: restart server + hard refresh browser

This ensures you always see the latest code and can debug effectively.
