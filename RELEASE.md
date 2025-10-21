# GitHub Release Instructions

## Automatic Release (Recommended)

GitHub Actions will automatically build and release the agent when you create a version tag:

1. **Update agent code** as needed

2. **Commit and push changes**:
   ```bash
   git add .
   git commit -m "Update agent for version 1.0.0"
   git push origin mul
   ```

3. **Create and push a version tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

4. **Wait for automatic build**:
   - GitHub Actions will automatically build the agent
   - Create a release at https://github.com/lizchen2025/SACMES_Web/releases
   - Upload the executable to the release

5. **Check the release**:
   - Go to https://github.com/lizchen2025/SACMES_Web/releases
   - Verify the new release is published with the executable

## Manual Release (If needed)

If you prefer to build locally:

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
