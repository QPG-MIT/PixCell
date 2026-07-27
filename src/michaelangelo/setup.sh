#!/bin/bash
# setup.sh - Create and configure virtual environment for Michaelangelo
#
# Usage: ./setup.sh
#
# This script creates a local Python virtual environment and installs
# all required dependencies for the component-to-GDS workflow.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Michaelangelo Setup"
echo "=========================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo ""
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt

# Verify key packages
echo ""
echo "Verifying key packages..."
python -c "import gdsfactory; print(f'  gdsfactory: {gdsfactory.__version__}')"
python -c "import google.genai; print('  google-genai: installed')"
python -c "import gdstk; print('  gdstk: installed')"

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Before running the workflow, set your Gemini API key:"
echo "  export GEMINI_API_KEY=your_api_key_here"
echo ""
echo "To run the full workflow for a component:"
echo "  ./run_workflow.sh component8"
echo ""
