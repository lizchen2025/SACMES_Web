# Build Troubleshooting

## Common Build Errors

### PermissionError: Access is denied

**Error Message:**
```
PermissionError: [WinError 5] Access is denied: 'dist\SACMES_Agent_Debug.exe'
```

**Cause:**
The executable file is currently running or locked by another process.

**Solution:**

1. Close all running agent instances
2. Use the process cleanup script:
   ```batch
   kill_agent_processes.bat
   ```
3. Wait 2 seconds
4. Run build script again

**Automatic Solution:**
All build scripts now automatically kill running agent processes before building.

### Module Not Found Errors

**Error Message:**
```
requests package is not installed
```

**Cause:**
Missing dependency in build environment.

**Solution:**
Verify all dependencies are installed:
```batch
test_dependencies.bat
```

### Build Hangs or Times Out

**Cause:**
- Antivirus scanning files
- Network issues downloading packages
- Insufficient system resources

**Solution:**
1. Temporarily disable antivirus
2. Ensure stable internet connection
3. Close other applications to free memory

## Build Scripts

### Standard Build
```batch
build_agent_minimal.bat
```
Creates GUI-only executable.

### Debug Build
```batch
build_agent_console.bat
```
Creates executable with console window for troubleshooting.

### Process Cleanup
```batch
kill_agent_processes.bat
```
Terminates all running agent processes.

### Full Cleanup
```batch
cleanup_build.bat
```
Removes all build artifacts and temporary files.

## Verification Steps

After successful build:

1. Check file exists:
   ```batch
   dir dist\SACMES_Agent*.exe
   ```

2. Test executable:
   ```batch
   dist\SACMES_Agent_Debug.exe
   ```

3. Verify connection to server

4. Test file monitoring functionality

## Getting Help

If issues persist:

1. Run debug build to view error messages
2. Check console output for specific errors
3. Verify Python version compatibility
4. Review CHANGELOG.md for recent fixes
