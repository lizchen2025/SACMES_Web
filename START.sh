#!/bin/bash

# ========================================
# SACMES Local Application Launcher
# For macOS and Linux
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "============================================"
echo "  SACMES Local Analysis System"
echo "  Starting..."
echo "============================================"
echo ""

# ----------------------------------------
# 1. Check Python Environment
# ----------------------------------------
echo "[1/5] Checking Python environment..."

PYTHON_EXE=""

# Method 1: Check for embedded Python (created by deploy_mac.sh)
if [ -f "$SCRIPT_DIR/python_embedded/bin/python" ] && [ -f "$SCRIPT_DIR/python_embedded/.embedded_marker" ]; then
    echo "[INFO] Found embedded Python environment"
    PYTHON_EXE="$SCRIPT_DIR/python_embedded/bin/python"
elif [ -f "$SCRIPT_DIR/python_embedded/bin/python3" ] && [ -f "$SCRIPT_DIR/python_embedded/.embedded_marker" ]; then
    echo "[INFO] Found embedded Python environment"
    PYTHON_EXE="$SCRIPT_DIR/python_embedded/bin/python3"
fi

# Method 2: Check for virtual environment
if [ -z "$PYTHON_EXE" ] && [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    echo "[INFO] Found virtual environment in venv/"
    PYTHON_EXE="$SCRIPT_DIR/venv/bin/python"
elif [ -z "$PYTHON_EXE" ] && [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    echo "[INFO] Found virtual environment in venv/"
    PYTHON_EXE="$SCRIPT_DIR/venv/bin/python3"
fi

# Method 3: Check for user-configured Python path
if [ -z "$PYTHON_EXE" ] && [ -f "$SCRIPT_DIR/python_path.txt" ]; then
    echo "[INFO] Found python_path.txt configuration file"
    CUSTOM_PYTHON=$(cat "$SCRIPT_DIR/python_path.txt" | tr -d '\r\n')

    if [ -f "$CUSTOM_PYTHON" ]; then
        echo "[INFO] Using configured Python: $CUSTOM_PYTHON"
        PYTHON_EXE="$CUSTOM_PYTHON"
    else
        echo "[WARNING] Configured Python path not found: $CUSTOM_PYTHON"
    fi
fi

# Method 4: Check for Python in system PATH
if [ -z "$PYTHON_EXE" ]; then
    for python_cmd in python3 python; do
        if command -v "$python_cmd" &> /dev/null; then
            version=$($python_cmd --version 2>&1 | awk '{print $2}')
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)

            if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                echo "[INFO] Found Python in system PATH"
                PYTHON_EXE="$python_cmd"
                break
            fi
        fi
    done
fi

# Python not found - auto-install embedded Python
if [ -z "$PYTHON_EXE" ]; then
    echo ""
    echo "============================================"
    echo "[INFO] Python environment not found"
    echo "============================================"
    echo ""
    echo "Installing embedded Python automatically..."
    echo ""
    sleep 1

    if [ -f "$SCRIPT_DIR/install_python_mac.sh" ]; then
        bash "$SCRIPT_DIR/install_python_mac.sh"

        # After installation, restart
        if [ -f "$SCRIPT_DIR/python_embedded/bin/python3" ]; then
            echo ""
            echo "Installation completed. Restarting application..."
            sleep 2
            exec "$0"
        else
            echo ""
            echo "Installation failed."
            echo "Exiting in 5 seconds..."
            sleep 5
            exit 1
        fi
    else
        echo "[ERROR] install_python_mac.sh not found!"
        echo ""
        echo "Please download the complete SACMES Local package."
        echo "Exiting in 5 seconds..."
        sleep 5
        exit 1
    fi
fi

# Check Python version
PYTHON_VERSION=$("$PYTHON_EXE" --version 2>&1 | awk '{print $2}')
major=$(echo "$PYTHON_VERSION" | cut -d. -f1)
minor=$(echo "$PYTHON_VERSION" | cut -d. -f2)

echo "[OK] Python version: $PYTHON_VERSION"
echo "[OK] Python location: $PYTHON_EXE"

# Validate version >= 3.9
if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 9 ]); then
    echo "[ERROR] Python version too low, need 3.9+"
    echo "Exiting in 5 seconds..."
    sleep 5
    exit 1
fi

# ----------------------------------------
# 2. Check Core Files
# ----------------------------------------
echo "[2/5] Checking core files..."

if [ ! -f "$SCRIPT_DIR/app_local.py" ]; then
    echo "[ERROR] app_local.py not found"
    echo "Exiting in 5 seconds..."
    sleep 5
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/data_processing" ]; then
    echo "[ERROR] data_processing directory not found"
    echo "Exiting in 5 seconds..."
    sleep 5
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/static" ]; then
    echo "[ERROR] static directory not found"
    echo "Exiting in 5 seconds..."
    sleep 5
    exit 1
fi

echo "[OK] Core files complete"

# ----------------------------------------
# 3. Check and Install Dependencies
# ----------------------------------------
echo "[3/5] Checking dependencies..."

# Check Flask
if ! "$PYTHON_EXE" -c "import flask" &> /dev/null; then
    echo "[Installing] Flask..."
    "$PYTHON_EXE" -m pip install "Flask>=2.3.0,<3.0.0" --quiet --disable-pip-version-check
fi

# Check Flask-SocketIO
if ! "$PYTHON_EXE" -c "import flask_socketio" &> /dev/null; then
    echo "[Installing] Flask-SocketIO..."
    "$PYTHON_EXE" -m pip install "Flask-SocketIO>=5.3.6" "python-socketio>=5.10.0" --quiet --disable-pip-version-check
fi

# Check NumPy
if ! "$PYTHON_EXE" -c "import numpy" &> /dev/null; then
    echo "[Installing] NumPy..."
    "$PYTHON_EXE" -m pip install "numpy>=1.24.0,<2.0.0" --quiet --disable-pip-version-check
fi

# Check SciPy
if ! "$PYTHON_EXE" -c "import scipy" &> /dev/null; then
    echo "[Installing] SciPy..."
    "$PYTHON_EXE" -m pip install "scipy>=1.10.0,<2.0.0" --quiet --disable-pip-version-check
fi

# Check watchdog
if ! "$PYTHON_EXE" -c "import watchdog" &> /dev/null; then
    echo "[Installing] watchdog..."
    "$PYTHON_EXE" -m pip install "watchdog>=3.0.0" --quiet --disable-pip-version-check
fi

echo "[OK] All dependencies installed"

# ----------------------------------------
# 4. Prepare Runtime Environment
# ----------------------------------------
echo "[4/5] Preparing runtime environment..."

mkdir -p "$SCRIPT_DIR/uploads"
mkdir -p "$SCRIPT_DIR/logs"

echo "[OK] Environment ready"

# macOS permission hint
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "[INFO] macOS tip: If SACMES cannot read your data folder,"
    echo "       run grant_permissions.sh to set up folder access."
    echo "       Or: System Settings > Privacy & Security > Full Disk Access > add Terminal"
fi

# ----------------------------------------
# 5. Start Service
# ----------------------------------------
echo "[5/5] Starting SACMES Local service..."
echo ""
echo "============================================"
echo "  Service will start on: http://127.0.0.1:5000"
echo "  (If port 5000 is busy, another port will be used)"
echo ""
echo "  Press Ctrl+C to stop the service"
echo "============================================"
echo ""

# Clean up old port file
rm -f "$SCRIPT_DIR/.sacmes_port"

# Open browser after detecting actual port (macOS and Linux)
(
    # Wait for port file to be created (max 10 seconds)
    for i in {1..20}; do
        if [ -f "$SCRIPT_DIR/.sacmes_port" ]; then
            ACTUAL_PORT=$(cat "$SCRIPT_DIR/.sacmes_port")
            # Use 127.0.0.1 explicitly — macOS may resolve 'localhost' to ::1 (IPv6)
            # but Flask listens on 127.0.0.1 (IPv4), causing connection refused
            echo "[INFO] Opening browser to http://127.0.0.1:$ACTUAL_PORT"

            if [[ "$OSTYPE" == "darwin"* ]]; then
                open "http://127.0.0.1:$ACTUAL_PORT"
            elif command -v xdg-open &> /dev/null; then
                xdg-open "http://127.0.0.1:$ACTUAL_PORT"
            elif command -v gnome-open &> /dev/null; then
                gnome-open "http://127.0.0.1:$ACTUAL_PORT"
            fi
            break
        fi
        sleep 0.5
    done
) &

# Start Flask application
"$PYTHON_EXE" "$SCRIPT_DIR/app_local.py"

EXIT_CODE=$?

# ----------------------------------------
# Cleanup and Exit
# ----------------------------------------
# Clean up port file
rm -f "$SCRIPT_DIR/.sacmes_port"

echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "Service stopped normally"
else
    echo "[ERROR] Service exited with error code: $EXIT_CODE"
    echo ""
    echo "Check logs directory for details"
fi
echo "============================================"
echo ""
echo "Window will close in 3 seconds..."
sleep 3
