# MCP with Mock Entra ID - Demos

This directory contains interactive demos and end-to-end tests for the complete MCP ecosystem with mock Entra ID authentication.

## Quick Start

### Run the Interactive Demo

```bash
cd demos/guided-demo
./demo.sh
```

This will:

1. Start the mock IdP and MCP server with Docker Compose
2. Wait for services to be healthy
3. Run a service principal authentication demo
4. Show token claims and MCP server responses
5. Provide links to explore further

### Manual Docker Compose

```bash
cd demos
docker compose -f docker-compose.demo.yml up -d

# Check health
curl http://localhost:8001/health  # Mock IdP
curl http://localhost:8000/health  # MCP Server

# Stop services
docker compose -f docker-compose.demo.yml down
```

## Demo Scenarios

### 1. Service Principal (Client Credentials) Flow

Demonstrates app-only authentication without user interaction:

```bash
# Get access token
curl -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=77777777-7777-7777-7777-777777777777" \
  -d "client_secret=test-sp-secret-456" \
  -d "scope=api://mcp-server/.default"

# Use token to call MCP server
curl http://localhost:8000/api/me \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

### 2. Authorization Code + PKCE Flow (Interactive)

Demonstrates user authentication with browser:

```bash
# Generate PKCE values
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-43)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | base64 | tr -d '=+/' | tr '/+' '_-')

# Navigate to authorization endpoint (in browser)
open "http://localhost:8001/oauth2/v2.0/authorize?client_id=33333333-3333-3333-3333-333333333333&redirect_uri=http://localhost:8080/callback&response_type=code&scope=api://mcp-server/.default&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256&state=random-state"

# After login and getting code from redirect, exchange for token
curl -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=33333333-3333-3333-3333-333333333333" \
  -d "code={AUTHORIZATION_CODE}" \
  -d "redirect_uri=http://localhost:8080/callback" \
  -d "code_verifier=$CODE_VERIFIER"
```

### 3. Inspect JWKS and Token Validation

```bash
# Get JWKS (public keys)
curl http://localhost:8001/discovery/v2.0/keys | jq

# Get OIDC discovery
curl http://localhost:8001/.well-known/openid-configuration | jq

# The MCP server uses these keys to validate tokens
```

### 4. MCP Protocol Demo

```bash
# Get token (service principal)
TOKEN=$(curl -s -X POST http://localhost:8001/oauth2/v2.0/token \
  -d "grant_type=client_credentials" \
  -d "client_id=77777777-7777-7777-7777-777777777777" \
  -d "client_secret=test-sp-secret-456" \
  -d "scope=api://mcp-server/.default" | jq -r '.access_token')

# Initialize MCP connection
curl -X POST http://localhost:8000/mcp/initialize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocolVersion":"2024-11-05",
    "capabilities":{},
    "clientInfo":{"name":"Demo","version":"1.0"}
  }' | jq

# List MCP tools
curl -X POST http://localhost:8000/mcp/tools/list \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq

# Call a tool
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"get_weather",
    "arguments":{"location":"San Francisco","units":"fahrenheit"}
  }' | jq
```

## Pre-configured Test Credentials

### Service Principals

- **Client ID:** `77777777-7777-7777-7777-777777777777`
- **Client Secret:** `test-sp-secret-456`
- **Roles:** `MCP.Read.All`, `MCP.ReadWrite.All`

### Confidential Clients

- **Client ID:** `66666666-6666-6666-6666-666666666666`
- **Client Secret:** `test-secret-123`

### Public Clients

- **VS Code:** `11111111-1111-1111-1111-111111111111`
- **Claude Code:** `33333333-3333-3333-3333-333333333333`

### Test Users

- `testuser@example.com`
- `admin@example.com`
- `demo@example.com`
- **Password:** Any password (authentication is mocked)

## Service URLs

- **Mock IdP:** http://localhost:8001
  - Login UI: http://localhost:8001/oauth2/v2.0/authorize (triggered by OAuth flow)
  - JWKS: http://localhost:8001/discovery/v2.0/keys
  - Discovery: http://localhost:8001/.well-known/openid-configuration

- **MCP Server:** http://localhost:8000
  - Swagger UI: http://localhost:8000/docs
  - Health: http://localhost:8000/health
  - User info: http://localhost:8000/api/me (requires auth)

## Playwright E2E Tests

Run browser automation tests:

```bash
cd demos/playwright-tests
npm install
npm test
```

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker info

# View logs
docker compose -f docker-compose.demo.yml logs

# Restart services
docker compose -f docker-compose.demo.yml restart
```

### Token validation fails

```bash
# Ensure MCP server is pointing to mock IdP JWKS
# Check MCP server environment:
docker compose -f docker-compose.demo.yml exec mcp-server env | grep ENTRA
```

### Browser flow doesn't work

Make sure you have a callback listener on http://localhost:8080/callback or use the provided client examples that include a callback server.

## Next Steps

- Try running the MCP client examples with the mock IdP
- Modify token TTLs and observe refresh behavior
- Test PKCE validation by using wrong code_verifier
- Experiment with different scopes and roles
