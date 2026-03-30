#!/bin/bash

# ========================================
# SACMES Local - Clear Python Cache
# For macOS and Linux
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================================"
echo "SACMES Local - Clear Python Cache"
echo "================================================================"
echo ""
echo "Clearing Python cache files..."

cd "$SCRIPT_DIR"

# Remove .pyc files
find . -name "*.pyc" -type f -delete 2>/dev/null

# Remove __pycache__ directories
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

echo ""
echo "[OK] Cache cleared successfully"
echo ""
echo "Now you can run ./START.sh to restart the application"
echo ""
read -p "Press Enter to exit..."
