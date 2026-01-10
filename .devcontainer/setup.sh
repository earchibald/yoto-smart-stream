#!/bin/bash

echo "🚀 Setting up Yoto Smart Stream development environment..."

# Upgrade pip
python -m pip install --upgrade pip

# Install development dependencies if requirements files exist
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
fi

if [ -f "requirements-dev.txt" ]; then
    echo "📦 Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Install pre-commit hooks if configuration exists
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🔧 Setting up pre-commit hooks..."
    pip install pre-commit
    pre-commit install
fi

echo "✅ Development environment setup complete!"
echo ""
echo "📚 Quick Start:"
echo "  - Run 'pytest' to run tests"
echo "  - Run 'python examples/simple_client.py' to test basic API connection"
echo "  - Check docs/ for architecture and implementation guidance"
echo ""
