#!/bin/bash
# Install script for ops-center-cli

set -e

echo "🚀 Installing Ops-Center CLI..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install in editable mode for development
if [ "$1" = "--dev" ]; then
    echo "Installing in development mode..."
    pip install -e ".[dev]"
else
    echo "Installing..."
    pip install .
fi

echo ""
echo "✅ Ops-Center CLI installed successfully!"
echo ""
echo "Quick start:"
echo "  1. Initialize configuration:"
echo "     ops-center init"
echo ""
echo "  2. Check server status:"
echo "     ops-center server status"
echo ""
echo "  3. List users:"
echo "     ops-center users list"
echo ""
echo "For help, run: ops-center --help"
