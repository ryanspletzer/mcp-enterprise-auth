#!/bin/bash
# Universal test runner with project selection
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo -e "${BLUE}MCP Enterprise Auth Test Runner${NC}"
    echo ""
    echo "Usage: $0 <test-suite> [pytest-args...]"
    echo ""
    echo "Test Suites:"
    echo "  server       Run MCP server tests"
    echo "  mock-idp     Run mock Entra IdP tests"
    echo "  client       Run MCP client example tests"
    echo "  all          Run all test suites"
    echo "  integration  Run integration tests with real Entra ID"
    echo "  interactive  Run browser-based e2e tests (requires manual sign-in)"
    echo ""
    echo "Examples:"
    echo "  $0 server                    # Run all server tests"
    echo "  $0 server -v                 # Run server tests with verbose output"
    echo "  $0 server -k test_jwt        # Run server tests matching 'test_jwt'"
    echo "  $0 all                       # Run all test suites"
    echo "  $0 integration               # Run integration tests with real Entra ID"
    echo "  $0 interactive               # Run browser-based tests"
    echo ""
}

if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

SUITE="$1"
shift

case "$SUITE" in
    server)
        "$SCRIPT_DIR/run-mcp-server-tests.sh" "$@"
        ;;
    mock-idp)
        "$SCRIPT_DIR/run-mock-idp-tests.sh" "$@"
        ;;
    client)
        "$SCRIPT_DIR/run-client-tests.sh" "$@"
        ;;
    all)
        "$SCRIPT_DIR/run-all-tests.sh" "$@"
        ;;
    integration)
        "$SCRIPT_DIR/run-integration-tests.sh" "$@"
        ;;
    interactive)
        "$SCRIPT_DIR/run-interactive-tests.sh" "$@"
        ;;
    -h|--help|help)
        show_usage
        exit 0
        ;;
    *)
        echo -e "${RED}Error: Unknown test suite '$SUITE'${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
