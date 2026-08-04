#!/bin/bash
# HOMI Setup Script
# Creates virtual environment and installs all dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "HOMI Setup"
echo "==================================="

# Find compatible Python (need <3.14 for gdsfactory)
# Prefer Homebrew installations on macOS; fall back to whatever python3.1x
# is on PATH (Linux distro packages, pyenv, uv-managed toolchains, ...)
PYTHON_CMD=""
for cmd in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
           /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 \
           "$(command -v python3.13 || true)" "$(command -v python3.12 || true)" "$(command -v python3.11 || true)"; do
    if [ -n "$cmd" ] && [ -x "$cmd" ]; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: No compatible Python found (need 3.11, 3.12, or 3.13 on PATH)"
    echo "macOS: brew install python@3.13    Linux: apt/dnf install python3.13 (or pyenv/uv)"
    exit 1
fi

echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install the package and its dependencies (this may take a few minutes)
echo "Installing PixCell (this may take a few minutes)..."
pip install -e ".[workbench,dev]"

# Install the package itself (editable) so the pixcell/homi CLI and MCP
# servers resolve (distribution: pixcell; import packages stay homi, gg, ...)
echo "Installing pixcell (editable)..."
pip install -e . --no-deps

# Handle .env file (keys are optional — the core loop runs without any)
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "Note: API keys are optional. The core loop (recreate, verify, gate,"
    echo "      workbench, studio) needs none; add GEMINI_API_KEY to .env only"
    echo "      for 'homi extract' on paper figures."
else
    echo ".env already exists"
fi

echo ""
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo ""
echo "To run PixCell/HOMI:"
echo "  source .venv/bin/activate"
echo "  homi studio        # chat-first front door"
echo "  homi --help        # every pipeline stage"
echo ""
