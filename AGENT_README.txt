================================================================================
SACMES Local Data Agent
================================================================================

The SACMES Agent is a local application that monitors a folder on your computer
and sends data files to the SACMES analysis platform for processing.

================================================================================
QUICK START
================================================================================

1. Extract all files from this ZIP to a folder of your choice

2. Double-click "start_agent.bat"

3. On first run, the agent will automatically:
   - Download a full Python environment with GUI support (30 MB)
   - Install required packages (5 MB)
   - This takes about 1-2 minutes with a good internet connection

4. After setup, the agent window will open automatically

5. Configure the agent:
   - Enter your SACMES server URL
   - Click "Select Folder" to choose the folder to monitor
   - Click "Start" to begin monitoring

================================================================================
SYSTEM REQUIREMENTS
================================================================================

- Windows 10 or Windows 11
- Internet connection (for setup and operation)
- Approximately 50 MB disk space
- Administrator rights NOT required

================================================================================
FILES INCLUDED
================================================================================

start_agent.bat      - Main launcher (double-click this to start)
install_python.bat   - First-time setup script (called automatically)
agent.py             - Agent program source code
Netzlab.ico          - Application icon
README.txt           - This file

================================================================================
FREQUENTLY ASKED QUESTIONS
================================================================================

Q: Is this safe to run?
A: Yes. This is a portable Python script. You can review the source code
   in agent.py. No installation to your system is required.

Q: Why does it download Python?
A: To ensure the agent runs correctly without requiring you to install
   Python yourself. The download is a portable version that only affects
   this folder.

Q: Where is data stored?
A: The agent does not store data locally. It monitors your selected folder
   and sends files to your SACMES server for analysis.

Q: Can I move this folder?
A: Yes. You can move the entire folder anywhere. Just run start_agent.bat
   from the new location.

Q: How do I uninstall?
A: Simply delete this entire folder. Nothing is installed to your system.

Q: Do I need to run install_python.bat manually?
A: No. start_agent.bat will automatically run it on first use.

================================================================================
TROUBLESHOOTING
================================================================================

Problem: Python installation fails or shows "installation failed"
Solution: The installer v3.1 uses embeddable Python only (most reliable):
          1. Check install_log.txt for detailed error information
          2. Common causes and fixes:
             - No internet: Check connection, download shows progress
             - Antivirus: Temporarily disable it
             - Firewall: Allow PowerShell to access python.org
             - Disk space: Need ~50 MB free
          3. Manual fix: Delete "sacmes_python" folder and try again
          4. Alternative: Manually download the ZIP (see error message for URL)

Problem: Python installer shows "Modify/Repair/Uninstall" dialog
Solution: v3.1 uses embeddable Python only - this should not happen anymore!
          If it still occurs:
          1. Close the dialog (click X, do NOT select any option)
          2. Delete the entire "sacmes_python" folder
          3. Delete any "python_embed" folder if it exists (old version)
          4. Run start_agent.bat again

Problem: "Python environment not found" appears repeatedly
Solution: Delete the "sacmes_python" folder and run start_agent.bat again
          The installer will re-run automatically

Problem: Installation stuck or freezes
Solution: 1. Press Ctrl+C to cancel
          2. Delete these files if they exist:
             - python-3.11.9-embed-amd64.zip
             - sacmes_python folder
          3. Run start_agent.bat again
          4. Check install_log.txt for errors

Problem: Cannot connect to server
Solution: Check your server URL and internet connection
          Make sure the URL starts with http:// or https://

Problem: Files are not being processed
Solution: Check that files in your monitored folder match the expected format
          Check the agent log window for error messages

Problem: GUI features not working (tkinter errors)
Solution: v3.1 uses embeddable Python which does not include tkinter.
          This is expected behavior. The agent works fine without GUI.
          If you need full GUI support, you must manually install Python 3.11.9
          from python.org and use it instead.

================================================================================
PRIVACY & DATA
================================================================================

The agent requires your explicit consent before monitoring any files.
You can review what data is accessed in the consent dialog.

The agent only sends data to the server URL you configure.

User ID and session tracking are used solely for multi-user support and
data isolation on the server.

================================================================================
SUPPORT
================================================================================

For issues or questions, please contact your SACMES administrator or
visit: https://github.com/lizchen2025/SACMES_Web

================================================================================
VERSION INFORMATION
================================================================================

Version: 3.1 (Embeddable-Only)
Last Updated: 2025-10-22

Changes in v3.1:
- Uses ONLY embeddable Python (no registry conflicts)
- Changed directory name from python_embed to sacmes_python
- Removed full installer fallback (caused Modify/Repair issues)
- Simplified installation process
- More detailed error messages and recovery steps

================================================================================
