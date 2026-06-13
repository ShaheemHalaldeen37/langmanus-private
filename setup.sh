#!/usr/bin/env bash
set -euo pipefail

# ── LangManus setup script ──────────────────────────────────────────────────
# Creates a Python virtual environment and installs all backend dependencies.
# Requires Python 3.11+.

PYTHON=$(command -v python3.11 || command -v python3.12 || command -v python3)
PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

echo "Using Python $PYTHON_VERSION at $PYTHON"

# Check minimum version
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"; then
  :
else
  echo "ERROR: Python 3.11 or higher is required (found $PYTHON_VERSION)." >&2
  exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating .venv..."
  "$PYTHON" -m venv .venv
else
  echo ".venv already exists, skipping creation."
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip --quiet

# Install project and all dependencies from pyproject.toml
echo "Installing dependencies..."
pip install -e ".[dev]" --quiet

# Install playwright browsers required by browser-use
echo "Installing Playwright browsers..."
playwright install chromium

# Remind about .env
if [ ! -f ".env" ]; then
  echo ""
  echo "⚠  No .env file found."
  echo "   Copy the example and fill in your API keys before starting the server:"
  echo ""
  echo "     cp .env.example .env"
  echo "     # then edit .env with your GROQ / TAVILY keys"
  echo ""
else
  echo ".env found."
fi

echo ""
echo "Setup complete. See instructions.md for how to start the server and web UI."
