#!/bin/bash

set -e

echo "🚀 Setting up Manifest development environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install project with dev dependencies (tests, lint)
echo "📥 Installing Python dependencies..."
pip install -e ".[dev]"

SYSTEM=$(uname -s)

# On macOS, ensure Homebrew is available (needed for OpenCode). Install automatically when missing.
if [ "$SYSTEM" = "Darwin" ] && ! command -v brew &> /dev/null; then
    echo ""
    echo "Homebrew: not found. Installing (required for OpenCode on macOS)..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    echo "Homebrew installed."
fi

# OpenCode is required (chat/commands). Install at setup time when missing (no user action needed).
echo ""
echo "OpenCode: checking installation (required for Manifest)..."
if ! command -v opencode &> /dev/null; then
    echo "Installing OpenCode (required; you do not need to install it yourself)..."
    if [ "$SYSTEM" = "Darwin" ] && command -v brew &> /dev/null; then
        brew install opencode
        echo "OpenCode installed."
    elif command -v npm &> /dev/null; then
        npm install -g opencode-ai
        echo "OpenCode installed."
    else
        echo "Could not auto-install OpenCode (need Homebrew on macOS or Node/npm)."
        echo "Manifest will try to install it when you run the app, or install manually: brew install opencode or npm install -g opencode-ai"
    fi
else
    echo "OpenCode is installed"
fi

echo ""
echo "✅ Python environment setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate, run:"
echo "  deactivate"
