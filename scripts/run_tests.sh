#!/bin/bash

# Test runner script for Manifest

set -e

echo "Running Manifest tests..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run pytest with src/ layout support
PYTHONPATH=src pytest tests/ -v

echo "Tests complete!"