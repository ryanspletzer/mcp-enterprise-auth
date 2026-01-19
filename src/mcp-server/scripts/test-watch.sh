#!/bin/bash
# Test watch script for continuous testing during development
# Uses uv for Python environment management
# Usage: ./scripts/test-watch.sh [pytest-args]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MCP Server Test Watch Mode (with uv)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if pytest-watch is available in the uv environment
if ! uv run python -c "import pytest_watch" 2>/dev/null; then
    echo -e "${RED}Error: pytest-watch is not installed in uv environment${NC}"
    echo "Installing pytest-watch..."
    uv sync --extra dev
fi

# Default pytest arguments
DEFAULT_ARGS="-v --tb=short --maxfail=1"

# Use provided args or defaults
PYTEST_ARGS="${@:-$DEFAULT_ARGS}"

# Run pytest-watch with uv
echo -e "${GREEN}Running tests with args: ${PYTEST_ARGS}${NC}"
echo ""

uv run ptw --clear --runner "pytest ${PYTEST_ARGS}"
