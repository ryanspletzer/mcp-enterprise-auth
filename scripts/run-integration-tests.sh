#!/bin/bash
# Run integration tests with real Entra ID configuration
# Requires .env file at repository root (created by Setup-EntraIdAppRegistrations.ps1)
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
cd "$REPO_ROOT/src/mcp-server"

echo -e "${GREEN}Running integration tests with real Entra ID...${NC}"
echo -e "${YELLOW}Working directory: $(pwd)${NC}"
echo -e "${YELLOW}Tenant ID: ${ENTRA_TENANT_ID:-not set}${NC}"
echo ""

# Run integration tests with uv (using python -m pytest for reliable execution)
uv run python -m pytest tests/integration/ -m integration "$@"
