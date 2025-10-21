# SACMES Agent Distribution

## Current Distribution Method

The agent is distributed as a ZIP file containing Python scripts with auto-setup.
This method provides zero antivirus false positives and requires no local environment setup.

## Package Contents

The SACMES_Agent.zip includes:
- agent.py: Main agent source code
- start_agent.bat: One-click launcher
- install_python.bat: Auto-setup script (runs on first launch)
- README.txt: User instructions
- Netzlab.ico: Application icon

## Packaging the Agent

When you update agent files, package them for distribution:

### Windows (Recommended)

Simply run the packaging script:

```bash
package_agent.bat
```

This will create static/downloads/SACMES_Agent.zip automatically.

### Manual Packaging

Or use PowerShell directly:

```bash
# From project root
powershell -Command "Compress-Archive -Path 'agent.py','start_agent.bat','install_python.bat','AGENT_README.txt','Netzlab.ico' -DestinationPath 'static/downloads/SACMES_Agent.zip' -Force"
```

### After Packaging

Commit and deploy:

```bash
git add static/downloads/SACMES_Agent.zip
git commit -m "Update agent package"
git push origin mul
```

The file will be available at: https://your-server/downloads/SACMES_Agent.zip

## User Installation Process

1. Download SACMES_Agent.zip from the web interface
2. Extract to any folder
3. Double-click start_agent.bat
4. First run automatically downloads Python (~25 MB) and dependencies (~5 MB)
5. Agent window opens automatically

## Benefits of This Approach

- No antivirus false positives (Python scripts, not exe)
- No local environment setup required (auto-downloads Python)
- Small initial download (90 KB)
- Transparent source code
- Cross-platform compatible (with minor bat to sh conversion)
- Easy updates (just replace agent.py)
