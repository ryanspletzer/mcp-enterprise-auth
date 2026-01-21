#!/bin/bash
# Run all test suites sequentially
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Running All Test Suites${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Track overall status
FAILED=0

# Run MCP server tests
echo -e "${YELLOW}[1/3] MCP Server Tests${NC}"
if "$SCRIPT_DIR/run-mcp-server-tests.sh" "$@"; then
    echo -e "${GREEN}MCP Server tests passed${NC}"
else
    echo -e "${RED}MCP Server tests failed${NC}"
    FAILED=1
fi
echo ""

# Run mock IdP tests
echo -e "${YELLOW}[2/3] Mock Entra IdP Tests${NC}"
if "$SCRIPT_DIR/run-mock-idp-tests.sh" "$@"; then
    echo -e "${GREEN}Mock IdP tests passed${NC}"
else
    echo -e "${RED}Mock IdP tests failed${NC}"
    FAILED=1
fi
echo ""

# Run client tests
echo -e "${YELLOW}[3/3] MCP Client Example Tests${NC}"
if "$SCRIPT_DIR/run-client-tests.sh" "$@"; then
    echo -e "${GREEN}Client tests passed${NC}"
else
    echo -e "${RED}Client tests failed${NC}"
    FAILED=1
fi
echo ""

# Summary
echo -e "${BLUE}======================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}  All test suites passed!${NC}"
else
    echo -e "${RED}  Some test suites failed${NC}"
fi
echo -e "${BLUE}======================================${NC}"

exit $FAILED
