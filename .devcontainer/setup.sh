#!/bin/bash

echo "🚀 Setting up Yoto Smart Stream development environment..."

# Upgrade pip
python -m pip install --upgrade pip

# Install Railway CLI for deployments
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm i -g @railway/cli
else
    echo "✓ Railway CLI already installed"
fi

# Install package with dev dependencies from pyproject.toml
if [ -f "pyproject.toml" ]; then
    echo "📦 Installing package with [dev] dependencies..."
    pip install -e .[dev]
else
    # Fallback to requirements files if pyproject.toml doesn't exist
    if [ -f "requirements.txt" ]; then
        echo "📦 Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
    fi

    if [ -f "requirements-dev.txt" ]; then
        echo "📦 Installing development dependencies..."
        pip install -r requirements-dev.txt
    fi
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
echo "🚀 Railway Deployments:"
echo "  - For GitHub Codespaces: Set RAILWAY_TOKEN in Codespaces secrets (user level)"
echo "  - For local devcontainer: Run 'railway login' to authenticate"
echo "  - Deploy with: './scripts/railway_ephemeral_env.sh deploy <env-name>'"
echo "  - See: docs/EPHEMERAL_RAILWAY_ENVIRONMENTS.md for full guide"
echo ""
echo "🔑 Railway Token Setup (Codespaces):"
if [ -n "$RAILWAY_TOKEN" ]; then
  echo "  ✅ RAILWAY_TOKEN is set and available"
  railway whoami &> /dev/null && echo "  ✅ Railway authentication verified" || echo "  ⚠️  Could not verify Railway auth (may still work)"
else
  echo "  ℹ️  RAILWAY_TOKEN not set. To enable Railway deployments:"
  echo "     1. Get token from https://railway.app/account/tokens"
  echo "     2. Add to Codespaces secrets: https://github.com/settings/codespaces"
  echo "     3. Restart Codespace to load the secret"
  echo "  OR"
  echo "     Run 'railway login' for local authentication"
fi
echo ""
