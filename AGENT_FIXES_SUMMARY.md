# Agent Stop and Reconnect Fixes

## Problems Fixed

### 1. Agent Hanging/Crashing on Stop
**Problem:** Clicking Stop button causes agent to freeze or crash

**Root Causes:**
- `agent_thread.join()` with no timeout blocked indefinitely
- Thread was waiting on file processing acknowledgments
- Disconnecting socket while thread was active caused race conditions

**Solutions Applied:**
- Added timeout-based thread join with 5 second max wait
- Check thread status periodically instead of blocking
- Do NOT disconnect socket on stop - keep connection alive
- Give thread 0.1s to see flag change before waiting

**Code Changes (agent.py lines 839-868):**
```python
def stop_monitoring_logic(self):
    global is_monitoring_active, agent_thread
    self.log("Setting monitoring flag to False...")
    is_monitoring_active = False

    # Give thread time to see flag change
    time.sleep(0.1)

    if agent_thread and agent_thread.is_alive():
        # Wait with timeout and periodic checks
        max_wait = 5
        wait_interval = 0.2
        elapsed = 0

        while agent_thread.is_alive() and elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval

        if agent_thread.is_alive():
            self.log("[Warning] Thread did not stop gracefully")
        else:
            self.log("Thread stopped successfully")
```

### 2. Cannot Reconnect After Stop
**Problem:** After stopping, clicking Start again shows "connection failed"

**Root Cause:**
- Old code called `sio.disconnect()` on stop
- Starting again tried to reconnect but connection was closed
- Socket.IO client was in disconnected state

**Solution Applied:**
- Keep socket connection alive when stopping monitoring
- Only stop the file monitoring thread, not the connection
- This allows instant restart without reconnection delay

**Code Change (agent.py line 833-837):**
```python
def stop_monitoring(self):
    self.log("Stopping process...")
    self.stop_monitoring_logic()
    # Do NOT disconnect - keep connection alive
    self.log("Connection maintained for quick restart")
```

### 3. Improved Thread Lifecycle in set_filters
**Problem:** Starting new analysis while previous one running could cause conflicts

**Solution Applied:**
- Use same graceful stop mechanism in `on_set_filters` handler
- Wait for previous thread to finish before starting new one
- Timeout after 5 seconds if thread won't stop

**Code Changes (agent.py lines 493-533):**
```python
@sio.on('set_filters')
def on_set_filters(data):
    # Gracefully stop existing thread
    if agent_thread and agent_thread.is_alive():
        is_monitoring_active = False

        # Wait with timeout
        max_wait = 5
        wait_interval = 0.2
        elapsed = 0

        while agent_thread.is_alive() and elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval

    # Start new monitoring
    is_monitoring_active = True
    # ... rest of logic
```

## Debug Tools Created

### Console EXE for Debugging
Two new build scripts create debug-friendly versions:

**1. build_agent_console.bat**
- Builds EXE with console window visible
- Shows all print statements and errors
- Includes Socket.IO debug logs
- Helps diagnose connection issues

**2. agent_console.spec**
- PyInstaller spec for console version
- Sets `console=True` instead of `False`
- Same exclusions as regular version

## Testing Scenarios

### Scenario 1: Stop and Restart Same Folder
1. Click "Connect & Start"
2. Wait for monitoring to begin
3. Click "Stop"
4. Expected: Stops smoothly within 5 seconds
5. Click "Connect & Start" again
6. Expected: Resumes immediately without reconnection

### Scenario 2: Stop and Change Folder
1. Start monitoring folder A
2. Click "Stop"
3. Click "Select Folder" and choose folder B
4. Click "Connect & Start"
5. Expected: Starts monitoring folder B smoothly

### Scenario 3: Server Triggers New Analysis
1. Start monitoring
2. Server sends new filters
3. Expected: Old thread stops, new thread starts
4. No hanging or errors

## Build Options

### Regular Version (No Console)
```batch
build_agent_minimal.bat
```
Output: `dist\SACMES_Agent_Minimal.exe`
- No console window
- Clean GUI-only experience
- For end users

### Debug Version (With Console)
```batch
build_agent_console.bat
```
Output: `dist\SACMES_Agent_Debug.exe`
- Console window showing all output
- Socket.IO connection logs
- Error tracebacks visible
- For debugging connection issues

### Using Spec Files Directly
```batch
# Regular version
pyinstaller agent_minimal.spec

# Debug version
pyinstaller agent_console.spec
```

## Connection Troubleshooting

If the EXE cannot connect:

1. **Run Debug Version First**
   ```batch
   dist\SACMES_Agent_Debug.exe
   ```
   Check console output for error messages

2. **Common Issues**
   - "Connection refused" - Server not running
   - "SSL error" - Certificate issue, try HTTP instead of HTTPS
   - "Timeout" - Firewall or network issue
   - "Module not found" - Build issue, rebuild with console version

3. **Test Socket.IO Connection**
   Debug version shows detailed Socket.IO logs:
   - Connection attempts
   - Transport selection (polling/websocket)
   - Error messages from server
   - Authentication status

## Technical Details

### Thread Stop Mechanism
- Uses boolean flag `is_monitoring_active`
- Thread checks flag in loop and during file operations
- 0.1s grace period before checking thread status
- 5 second maximum wait with 0.2s check intervals
- Non-blocking, prevents GUI freeze

### Socket Connection Lifecycle
- Connect on "Connect & Start"
- Stay connected through stop/start cycles
- Only disconnect when:
  - User closes application
  - Connection error occurs
  - Explicit disconnect requested

### File Processing Flow
```
Start -> Connect -> Wait for filters -> Start thread
Stop -> Set flag False -> Wait for thread -> Keep connection
Restart -> Reuse connection -> Start new thread
```

## Files Modified

1. **agent.py** - Core fixes to stop/reconnect logic
2. **build_agent_console.bat** - New debug build script
3. **agent_console.spec** - New debug spec file
4. **AGENT_FIXES_SUMMARY.md** - This documentation

## Files Created

- build_agent_console.bat
- agent_console.spec
- AGENT_FIXES_SUMMARY.md

## Next Steps

1. Test Python script version first
   ```batch
   python agent.py
   ```

2. If script works, build debug EXE
   ```batch
   build_agent_console.bat
   ```

3. Test debug EXE, check console output

4. If debug EXE works, build regular EXE
   ```batch
   build_agent_minimal.bat
   ```

5. Deploy regular EXE to users
