#!/bin/bash
# Run interactive browser-based e2e tests with Playwright
# Opens a visible browser where user manually signs in to Entra ID
# Requires .env file at repository root (created by Setup-EntraIdAppRegistrations.ps1)
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check for .env file
ENV_FILE="$REPO_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    echo ""
    echo "To create the .env file, run the Entra ID setup script:"
    echo "  pwsh $REPO_ROOT/scripts/Setup-EntraIdAppRegistrations.ps1"
    echo ""
    exit 1
fi

# Load environment variables from .env
echo -e "${YELLOW}Loading environment from: $ENV_FILE${NC}"
set -a
source "$ENV_FILE"
set +a

# Change to project directory
cd "$REPO_ROOT/src/mcp-client-examples"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Interactive OAuth Tests${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "${GREEN}Running interactive e2e tests with Playwright...${NC}"
echo -e "${YELLOW}Working directory: $(pwd)${NC}"
echo -e "${YELLOW}Tenant ID: ${ENTRA_TENANT_ID:-not set}${NC}"
echo ""
echo -e "${YELLOW}NOTE: A browser window will open for manual sign-in.${NC}"
echo -e "${YELLOW}      You have 2 minutes to complete authentication.${NC}"
echo ""

# Ensure Playwright browsers are installed
echo -e "${YELLOW}Ensuring Playwright browsers are installed...${NC}"
uv run playwright install chromium --with-deps 2>/dev/null || uv run playwright install chromium

echo ""

# Run e2e tests with headed browser (using python -m pytest for reliable execution)
uv run python -m pytest tests/e2e/ --headed -v -s "$@"
