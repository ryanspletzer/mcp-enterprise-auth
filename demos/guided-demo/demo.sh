#!/bin/bash
# Interactive demo script for Mock Entra ID + MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Mock Entra ID + MCP Server Demo${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Start services
echo -e "${YELLOW}[1/6] Starting services...${NC}"
cd ..
docker compose -f docker-compose.demo.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}[2/6] Waiting for services to be healthy...${NC}"
echo -n "Waiting for Mock IdP"
while ! curl -sf http://localhost:8001/health > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e " ${GREEN}✓${NC}"

echo -n "Waiting for MCP Server"
while ! curl -sf http://localhost:8000/health > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e " ${GREEN}✓${NC}"

echo ""
echo -e "${GREEN}All services are healthy!${NC}"
echo ""

# Show available endpoints
echo -e "${YELLOW}[3/6] Service endpoints:${NC}"
echo -e "  Mock IdP:    ${BLUE}http://localhost:8001${NC}"
echo -e "  MCP Server:  ${BLUE}http://localhost:8000${NC}"
echo -e "  MCP Swagger: ${BLUE}http://localhost:8000/docs${NC}"
echo ""

# Show demo scenarios
echo -e "${YELLOW}[4/6] Available demo scenarios:${NC}"
echo ""
echo "  1. Service Principal (Client Credentials) Flow"
echo "  2. Inspect JWKS endpoint"
echo "  3. Test token validation"
echo "  4. View MCP server capabilities"
echo ""

# Run service principal demo
echo -e "${YELLOW}[5/6] Demo: Service Principal Flow${NC}"
echo -e "${BLUE}-----------------------------------${NC}"
echo ""

echo "Getting access token via client_credentials grant..."
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=77777777-7777-7777-7777-777777777777" \
  -d "client_secret=test-sp-secret-456" \
  -d "scope=api://mcp-server/.default")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}Failed to get access token${NC}"
    echo "Response: $TOKEN_RESPONSE"
else
    echo -e "${GREEN}✓ Access token obtained${NC}"
    echo ""

    # Decode token to show claims
    echo "Token claims (decoded):"
    echo $ACCESS_TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Error decoding token"
    echo ""

    # Call MCP server with token
    echo "Calling MCP Server /api/me endpoint..."
    ME_RESPONSE=$(curl -s http://localhost:8000/api/me \
      -H "Authorization: Bearer $ACCESS_TOKEN")

    echo -e "${GREEN}✓ MCP Server response:${NC}"
    echo $ME_RESPONSE | python3 -m json.tool
    echo ""

    # Call MCP initialize endpoint
    echo "Calling MCP Server /mcp/initialize endpoint..."
    INIT_RESPONSE=$(curl -s -X POST http://localhost:8000/mcp/initialize \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"Demo Client","version":"1.0"}}')

    echo -e "${GREEN}✓ MCP Initialize response:${NC}"
    echo $INIT_RESPONSE | python3 -m json.tool
fi

echo ""
echo -e "${YELLOW}[6/6] Demo complete!${NC}"
echo ""
echo -e "Additional things to try:"
echo -e "  • Visit ${BLUE}http://localhost:8001/docs${NC} for Mock IdP API docs"
echo -e "  • Visit ${BLUE}http://localhost:8000/docs${NC} for MCP Server API docs"
echo -e "  • Check JWKS: ${BLUE}curl http://localhost:8001/discovery/v2.0/keys${NC}"
echo -e "  • OIDC discovery: ${BLUE}curl http://localhost:8001/.well-known/openid-configuration${NC}"
echo ""

# Cleanup prompt
read -p "Stop and remove services? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping services..."
    docker compose -f docker-compose.demo.yml down
    echo -e "${GREEN}Services stopped${NC}"
else
    echo "Services still running. Stop with: docker compose -f docker-compose.demo.yml down"
fi
