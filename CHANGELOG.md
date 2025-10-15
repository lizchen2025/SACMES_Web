# Changelog

## 2025-01-14

### Agent Fixes

#### Stop/Restart Issues
- Fixed thread blocking on stop operation
- Implemented graceful thread shutdown with timeout
- Connection now maintained between stop/start cycles
- Eliminated crashes during stop operation

#### Reconnection Support
- Agent maintains Socket.IO connection when stopping monitoring
- Instant restart capability without reconnection delay
- Improved thread lifecycle management in filter updates

### Build System

#### Missing Dependencies
- Added `requests` package to requirements
- Updated all build scripts to install requests
- Added requests and urllib3 to hidden imports in spec files

#### Console Debug Build
- Created `build_agent_console.bat` for debugging
- Added `agent_console.spec` configuration
- Console version displays full error messages and logs

### Documentation

#### New Files
- BUILD_INSTRUCTIONS.md: Formal build documentation
- CHANGELOG.md: Version history
- FIXED_BUILD_SUMMARY.md: Technical details of urllib fix
- AGENT_FIXES_SUMMARY.md: Stop/reconnect fix details

#### Updated Files
- requirements_agent_minimal.txt: Added requests dependency
- All build scripts: Updated to install requests
- agent_minimal.spec: Added requests to hidden imports
- agent_console.spec: Added requests to hidden imports

### Code Changes

#### agent.py
- Modified `stop_monitoring_logic()`: Graceful thread shutdown
- Modified `stop_monitoring()`: Maintain connection
- Modified `on_set_filters()`: Improved thread lifecycle

## Build Instructions

Standard build:
```batch
build_agent_minimal.bat
```

Debug build:
```batch
build_agent_console.bat
```

## Testing

Test Python script:
```batch
python agent.py
```

Test executable:
```batch
dist\SACMES_Agent_Debug.exe
```
