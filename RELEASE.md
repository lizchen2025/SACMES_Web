# GitHub Release Instructions

## Creating a New Release

1. Build the agent executable:
   ```bash
   pyinstaller agent_minimal.spec
   ```

2. The executable will be in `dist/SACMES_Agent_Minimal.exe`

3. Create a new release on GitHub:
   - Go to https://github.com/lizchen2025/SACMES_Web/releases
   - Click "Create a new release"
   - Tag version: e.g., `v1.0.0`
   - Release title: e.g., `SACMES Agent v1.0.0`
   - Description template below

4. Upload the executable:
   - Drag and drop `SACMES_Agent_Minimal.exe` to the release assets
   - Publish release

## Release Description Template

```
## SACMES Local Data Agent

This is the local agent application for SACMES electrochemical analysis platform.

### What's New
- Multi-user session support
- Improved connection stability
- Optimized stop/folder switching
- (Add other changes here)

### Installation

1. Download `SACMES_Agent_Minimal.exe` from the assets below
2. Run the executable (no installation required)
3. Configure your SACMES server URL
4. Select folder to monitor
5. Click Start to begin analysis

### System Requirements

- Windows 10/11
- Internet connection for server communication

### Source Code

Full source code is available in this repository under the mul branch.

### Security Note

This agent is open source and distributed through GitHub to ensure transparency and reduce false positives from antivirus software. You can review the source code before running.

### Support

For issues or questions, please open an issue in this repository.
```

## Notes

- Always use semantic versioning (e.g., v1.0.0, v1.1.0, v2.0.0)
- Keep release descriptions clear and user-friendly
- Include any breaking changes prominently
- Update the web application's download link if repository structure changes
