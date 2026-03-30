SACMES Local - Beta 0.0.4
Electrochemical analysis software for SWV and CV data.
===========================================================


WINDOWS
-------

Double-click START.bat to launch.

If Python is not installed, START.bat will open a setup wizard automatically.


MACOS
-----

macOS blocks downloaded scripts by default. Follow the steps below.


Step 1 -- One-time setup (copy and paste into Terminal)

    cd ~/Downloads/SACMES_Beta_0.0.4
    xattr -dr com.apple.quarantine .
    chmod +x START.sh CLEAR_CACHE.sh install_python_mac.sh
    ./START.sh

  - Replace ~/Downloads/SACMES_Beta_0.0.4 with the actual path to your
    folder if you extracted it somewhere else.
  - xattr -dr com.apple.quarantine . removes the quarantine restriction
    that macOS applies to all files downloaded from the internet.
    You only need to run this once.


Step 2 -- Every time after that

Open Terminal and run:

    cd ~/Downloads/SACMES_Beta_0.0.4 && ./START.sh

The app will open automatically in your browser at http://127.0.0.1:5000


Python not installed?

  START.sh will detect this and install a Python environment automatically.
  If you prefer to install Python manually:

    brew install python@3.11

  Or download from: https://www.python.org/downloads/


macOS folder access (if SACMES cannot read your data folder)

  macOS may block access to Desktop, Documents, Downloads, or external drives.

  Fix: System Settings > Privacy & Security > Full Disk Access
       Click + and add Terminal
       Restart Terminal and run ./START.sh again


UTILITIES
---------

  START.bat          Windows         Launch app
  START.sh           macOS / Linux   Launch app
  CLEAR_CACHE.bat    Windows         Clear Python cache if app behaves oddly
  CLEAR_CACHE.sh     macOS / Linux   Clear Python cache if app behaves oddly
