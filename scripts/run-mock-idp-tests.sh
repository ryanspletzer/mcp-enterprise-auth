#!/bin/bash
# Run mock Entra IdP tests
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Change to project directory
cd "$REPO_ROOT/src/mock-entra-idp"

echo -e "${GREEN}Running mock Entra IdP tests...${NC}"
echo -e "${YELLOW}Working directory: $(pwd)${NC}"
echo ""

# Run tests with uv (using python -m pytest for reliable execution)
uv run python -m pytest tests/ "$@"
