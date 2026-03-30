#!/bin/bash

# ========================================
# SACMES Local - Automatic Python Setup
# Downloads and installs embedded Python if needed
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.11.7"

echo ""
echo "============================================"
echo "  SACMES - Installing Embedded Python"
echo "============================================"
echo ""

# Check if embedded Python already exists
if [ -f "$SCRIPT_DIR/python_embedded/bin/python3" ]; then
    echo "[INFO] Embedded Python already installed"
    exit 0
fi

echo "[1/4] Checking system requirements..."

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "[ERROR] This script is for macOS only"
    echo "For Linux, use system Python instead"
    exit 1
fi

# Detect architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    PYTHON_PKG="python-${PYTHON_VERSION}-macos11.pkg"
    echo "[INFO] Detected Apple Silicon (M1/M2)"
elif [[ "$ARCH" == "x86_64" ]]; then
    PYTHON_PKG="python-${PYTHON_VERSION}-macos11.pkg"
    echo "[INFO] Detected Intel processor"
else
    echo "[ERROR] Unsupported architecture: $ARCH"
    exit 1
fi

PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_PKG}"

echo "[OK] System check passed"
echo ""

echo "[2/4] Creating embedded Python environment..."
echo "Searching for existing Python, will download if not found..."
echo ""

# Find system Python
SYSTEM_PYTHON=""
for python_cmd in python3.11 python3.10 python3.9 python3 python; do
    if command -v "$python_cmd" &> /dev/null; then
        version=$($python_cmd --version 2>&1 | awk '{print $2}')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)

        if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
            SYSTEM_PYTHON="$python_cmd"
            echo "[INFO] Using $python_cmd (version $version)"
            break
        fi
    fi
done

# No system Python found — download and install the official package
if [ -z "$SYSTEM_PYTHON" ]; then
    echo "[INFO] Python 3.9+ not found. Downloading Python ${PYTHON_VERSION}..."
    echo ""

    DOWNLOAD_DIR=$(mktemp -d)
    PKG_PATH="$DOWNLOAD_DIR/$PYTHON_PKG"

    echo "Downloading: $PYTHON_URL"
    echo "(This may take a few minutes depending on your connection speed)"
    echo ""

    if command -v curl &> /dev/null; then
        curl -L --progress-bar -o "$PKG_PATH" "$PYTHON_URL"
        DOWNLOAD_STATUS=$?
    elif command -v wget &> /dev/null; then
        wget --show-progress -O "$PKG_PATH" "$PYTHON_URL"
        DOWNLOAD_STATUS=$?
    else
        echo "[ERROR] Neither curl nor wget found. Cannot download Python automatically."
        echo ""
        echo "Please install Python manually, then re-run START.sh:"
        echo "  brew install python@3.11"
        echo "  or: https://www.python.org/downloads/"
        rm -rf "$DOWNLOAD_DIR"
        exit 1
    fi

    if [ $DOWNLOAD_STATUS -ne 0 ] || [ ! -f "$PKG_PATH" ]; then
        echo "[ERROR] Download failed. Check your internet connection."
        rm -rf "$DOWNLOAD_DIR"
        exit 1
    fi

    echo ""
    echo "Installing Python ${PYTHON_VERSION}..."
    echo "(Administrator password may be required)"
    echo ""

    sudo installer -pkg "$PKG_PATH" -target /
    INSTALL_STATUS=$?
    rm -rf "$DOWNLOAD_DIR"

    if [ $INSTALL_STATUS -ne 0 ]; then
        echo "[ERROR] Python installation failed."
        echo "Try installing manually: https://www.python.org/downloads/"
        exit 1
    fi

    # Re-scan after installation (official .pkg installs to /Library/Frameworks)
    FRAMEWORK_PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"
    if [ -f "$FRAMEWORK_PYTHON" ]; then
        SYSTEM_PYTHON="$FRAMEWORK_PYTHON"
        echo "[OK] Python installed: $FRAMEWORK_PYTHON"
    else
        for python_cmd in python3.11 python3.10 python3.9 python3; do
            if command -v "$python_cmd" &> /dev/null; then
                version=$($python_cmd --version 2>&1 | awk '{print $2}')
                major=$(echo "$version" | cut -d. -f1)
                minor=$(echo "$version" | cut -d. -f2)
                if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
                    SYSTEM_PYTHON="$python_cmd"
                    echo "[OK] Python installed: $python_cmd (version $version)"
                    break
                fi
            fi
        done
    fi

    if [ -z "$SYSTEM_PYTHON" ]; then
        echo "[ERROR] Installation completed but Python still not found."
        echo "Please close this window, open a new Terminal, and re-run START.sh."
        exit 1
    fi
fi

# Create virtual environment as embedded Python
echo ""
echo "Creating portable Python environment..."
$SYSTEM_PYTHON -m venv "$SCRIPT_DIR/python_embedded"

if [ ! -f "$SCRIPT_DIR/python_embedded/bin/python3" ]; then
    echo "[ERROR] Failed to create Python environment"
    exit 1
fi

# Create marker file
touch "$SCRIPT_DIR/python_embedded/.embedded_marker"

echo "[OK] Python environment created"
echo ""

echo "[3/4] Upgrading pip..."
"$SCRIPT_DIR/python_embedded/bin/python3" -m pip install --upgrade pip --quiet --disable-pip-version-check

echo "[OK] Pip upgraded"
echo ""

echo "[4/4] Installing dependencies..."
echo "This may take 2-3 minutes..."

"$SCRIPT_DIR/python_embedded/bin/python3" -m pip install -r "$SCRIPT_DIR/requirements_local.txt" --quiet --disable-pip-version-check

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo "[OK] All dependencies installed"
echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "Embedded Python location: $SCRIPT_DIR/python_embedded/"
echo ""
echo "You can now run: ./START.sh"
echo ""
