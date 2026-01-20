#!/bin/bash

set -e

echo "🐳 Setting up Docker environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "Please install Docker Desktop for macOS:"
    echo "  1. Visit: https://www.docker.com/products/docker-desktop"
    echo "  2. Download and install Docker Desktop"
    echo "  3. Start Docker Desktop"
    echo "  4. Run this script again"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running."
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is installed and running"

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

echo ""
echo "✅ Docker environment setup complete!"
echo ""
echo "To run the application with Docker:"
echo "  docker-compose up"
echo ""
echo "To run in detached mode:"
echo "  docker-compose up -d"
echo ""
echo "To stop:"
echo "  docker-compose down"