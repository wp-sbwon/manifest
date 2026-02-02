#!/bin/bash

set -e

echo "🚀 Setting up Manifest development environment..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
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

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

SYSTEM=$(uname -s)

# On macOS, ensure Homebrew is available (needed for Podman/OpenCode). Install automatically when missing.
if [ "$SYSTEM" = "Darwin" ] && ! command -v brew &> /dev/null; then
    echo ""
    echo "Homebrew: not found. Installing (required for Podman/OpenCode on macOS)..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    echo "Homebrew installed."
fi

# Podman is required (Worker Squad runs in containers). Install at setup time when missing (no user action needed).
echo ""
echo "Podman: checking installation (required for Manifest)..."
if ! command -v podman &> /dev/null; then
    echo "Installing Podman (required; you do not need to install it yourself)..."
    if [ "$SYSTEM" = "Darwin" ] && command -v brew &> /dev/null; then
        brew install podman
        if ! podman machine list --noheading 2>/dev/null | grep -q .; then
            echo "Initializing Podman machine (first time)..."
            podman machine init --now
        fi
        echo "Podman installed. Manifest will start it automatically when you run the app."
    elif [ "$SYSTEM" = "Linux" ]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y podman
            sudo systemctl enable --now podman.socket 2>/dev/null || sudo systemctl enable --now podman 2>/dev/null || true
            echo "Podman installed."
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y podman
            sudo systemctl enable --now podman.socket 2>/dev/null || sudo systemctl enable --now podman 2>/dev/null || true
            echo "Podman installed."
        else
            echo "Could not auto-install Podman. Install manually: https://podman.io/getting-started/installation"
        fi
    else
        echo "On Windows: run setup in WSL or install Podman: winget install RedHat.Podman; then podman machine init"
    fi
else
    echo "Podman is installed"
    if podman info &> /dev/null; then
        echo "Podman is running (Docker-compatible API available)."
    else
        echo "Podman daemon/socket is not running. Manifest will start it automatically when you run the app."
    fi
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
