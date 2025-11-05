# SACMES Local Agent

## Overview

The SACMES Local Agent is a client-side application that monitors local directories and synchronizes data with the SACMES web platform. This package provides a portable Python environment for users who do not have Python installed on their system.

## System Requirements

- Operating System: Windows 10 or later (64-bit)
- Disk Space: Approximately 100 MB
- Network: Internet connection required for initial setup and operation
- Permissions: Standard user privileges (administrator rights not required)

## Installation Options

### Option 1: Portable Environment (Recommended for most users)

If you do not have Python installed or prefer an isolated environment:

1. Extract all files from the distribution package to a folder
2. Run `start_agent.bat`
3. The first run will automatically download and configure Python (~10 MB download)
4. Follow the on-screen instructions

The portable environment includes:
- Python 3.11.9 (embeddable distribution)
- tkinter GUI library (pre-packaged)
- Required packages: python-socketio, requests

### Option 2: Use Existing Python Environment

If you have Python 3.8 or later installed on your system:

1. Extract `agent.py` from the distribution package
2. Install required packages:
   ```
   pip install python-socketio requests
   ```
3. Run the agent:
   ```
   python agent.py
   ```

## Configuration

The agent requires the following configuration on first run:

- **Server URL**: The SACMES web server address (provided by your administrator)
- **Monitored Directory**: Local directory to monitor for changes
- **User Consent**: Agreement to data access terms

Configuration is saved locally and persists between sessions.

## Usage

### Starting the Agent

**Portable environment:**
```
start_agent.bat
```

**Existing Python environment:**
```
python agent.py
```

### Stopping the Agent

Click the "Stop Monitoring" button in the GUI or close the application window.

### Troubleshooting

**Agent fails to start:**
- Verify that all files were extracted from the distribution package
- Check that `tkinter_package` folder is present (portable environment only)
- Review `install_log.txt` for detailed error messages

**Cannot connect to server:**
- Verify the server URL is correct
- Check your internet connection
- Ensure firewall is not blocking the connection

**tkinter import error (portable environment):**
- Delete the `sacmes_python` folder
- Run `start_agent.bat` again to reinstall

**For other issues:**
- Check `install_log.txt` for diagnostic information
- Contact your system administrator

## File Structure

```
SACMES_Agent/
├── agent.py                      # Main agent application
├── start_agent.bat               # Launcher for portable environment
├── install_portable_python.bat   # Portable Python installer
├── download_file.ps1             # Download utility script
├── tkinter_package/              # Pre-packaged tkinter library
│   ├── Lib/
│   ├── DLLs/
│   └── tcl/
└── README.md                     # This file
```

After first run:
```
SACMES_Agent/
├── sacmes_python/                # Portable Python installation (auto-created)
└── install_log.txt               # Installation log (auto-created)
```

## Data Privacy

The SACMES Agent accesses and transmits data from the monitored directory only. No other files or system information are accessed. All data transmission is subject to the consent agreement presented on first run.

## Updates

To update the agent:
1. Download the latest distribution package
2. Extract to a new folder
3. Copy your configuration if needed (stored in agent.py directory)

## Support

For technical support or questions, please contact your system administrator or refer to the SACMES documentation.

## Version Information

- Agent Version: 4.0
- Python Version: 3.11.9
- Distribution Type: Portable with pre-packaged tkinter

## License

This software is provided for use with the SACMES platform. Refer to your organization's licensing agreement for terms of use.
