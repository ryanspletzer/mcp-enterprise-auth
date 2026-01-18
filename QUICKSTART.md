# Quick Start Guide

Get the MCP server running in 5 minutes!

## Prerequisites

- **uv** - Fast Python package manager ([install guide](./UV_SETUP.md))
- Docker and Docker Compose installed
- Microsoft Entra ID tenant
- 8 app registrations created in Entra ID (see [docs/setup/entra-id-setup.md](./docs/setup/entra-id-setup.md))

## Step 1: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your Entra ID configuration
nano .env  # or vim, code, etc.
```

**Required values to set:**
```bash
ENTRA_TENANT_ID=your-tenant-id-here
MCP_SERVER_APP_ID=api://mcp-server  # or your app ID URI
REQUIRED_SCOPE="mcp.read mcp.write"
REQUIRED_ROLE=MCP.ReadWrite.All

# Client IDs from Entra ID
VSCODE_CLIENT_ID=your-vscode-client-id
CLAUDE_DESKTOP_CLIENT_ID=your-claude-desktop-client-id
CLAUDE_CODE_CLIENT_ID=your-claude-code-client-id
CHATGPT_CLIENT_ID=your-chatgpt-client-id
GENERIC_CLIENT_ID=your-generic-client-id
```

## Step 2: Start the Server

```bash
# Start MCP server
docker-compose up -d mcp-server

# View logs
docker-compose logs -f mcp-server
```

You should see:
```text
mcp-server  | {"timestamp": "2026-01-17T...", "level": "INFO", "message": "mcp_server_starting"}
mcp-server  | {"timestamp": "2026-01-17T...", "level": "INFO", "message": "configuration_loaded"}
```

## Step 3: Test the Server

### Test Health Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status":"healthy"}

# Readiness check
curl http://localhost:8000/ready

# Expected: {"status":"ready","checks":{...}}

# API info
curl http://localhost:8000/

# Expected: {"name":"MCP Server with Proper Enterprise Authentication",...}
```

### Test DCR Emulation

```bash
# Test VS Code client detection
curl -X POST http://localhost:8000/dcr/register \
  -H "Content-Type: application/json" \
  -H "User-Agent: VSCode-MCP/1.0" \
  -d '{
    "redirect_uris": ["vscode://mcp-auth/callback"],
    "client_name": "VS Code MCP Client"
  }' | jq

# Expected:
# {
#   "client_id": "your-vscode-client-id",
#   "authorization_endpoint": "https://login.microsoftonline.com/.../oauth2/v2.0/authorize",
#   "token_endpoint": "https://login.microsoftonline.com/.../oauth2/v2.0/token",
#   ...
# }
```

### Test JWT Validation (with real token)

First, get a token from Entra ID using OAuth flow. Here's a quick way using `curl`:

```bash
# Step 1: Get authorization code (open in browser)
TENANT_ID="your-tenant-id"
CLIENT_ID="your-client-id"  # e.g., VSCODE_CLIENT_ID
REDIRECT_URI="http://localhost:8080/callback"
SCOPE="api://mcp-server/.default"

# Generate PKCE code verifier and challenge
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-43)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -binary -sha256 | openssl base64 | tr -d "=+/" | cut -c1-43)

# Authorization URL (paste in browser)
echo "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/authorize?client_id=$CLIENT_ID&response_type=code&redirect_uri=$REDIRECT_URI&scope=$SCOPE&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"

# Step 2: After login, you'll be redirected to redirect_uri with code parameter
# Extract the code from URL: http://localhost:8080/callback?code=AUTHORIZATION_CODE

# Step 3: Exchange code for token
CODE="authorization-code-from-redirect"

curl -X POST "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
  -d "client_id=$CLIENT_ID" \
  -d "grant_type=authorization_code" \
  -d "code=$CODE" \
  -d "redirect_uri=$REDIRECT_URI" \
  -d "code_verifier=$CODE_VERIFIER" \
  | jq -r '.access_token' > token.txt

# Step 4: Test MCP server with token
TOKEN=$(cat token.txt)

curl http://localhost:8000/api/me \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected:
# {
#   "token_type": "user",
#   "identity": {
#     "user_id": "...",
#     "user_principal": "user@example.com",
#     ...
#   },
#   "permissions": {
#     "scopes": ["mcp.read", "mcp.write"]
#   }
# }
```

## Step 4: Access Swagger UI

Open in browser: http://localhost:8000/docs

You'll see interactive API documentation with all endpoints.

## Step 5: Test with Mock Authentication (Optional, for Testing Only)

**WARNING**: Only for local testing! Never enable in production!

```bash
# Edit .env
ENABLE_MOCK_AUTH=true

# Restart server
docker-compose restart mcp-server

# Call protected endpoint without token
curl http://localhost:8000/api/me | jq

# Expected: Returns mock user data
```

## Common Issues

### "Configuration loaded" not appearing

Check that all required environment variables are set in `.env`:
```bash
docker-compose config | grep ENTRA_TENANT_ID
```

### DCR returns wrong client_id

The client detection is based on redirect_uri and User-Agent. Try:
1. Match redirect_uri exactly (e.g., `vscode://mcp-auth/callback`)
2. Include appropriate User-Agent header
3. Check logs: `docker-compose logs mcp-server | grep client_detected`

### JWT validation fails

1. Verify token is from correct tenant:
   ```bash
   # Decode token (without verification)
   echo "$TOKEN" | cut -d. -f2 | base64 -d | jq
   # Check "tid" matches ENTRA_TENANT_ID
   # Check "aud" matches MCP_SERVER_APP_ID
   ```

2. Check token hasn't expired:
   ```bash
   # Check "exp" claim
   echo "$TOKEN" | cut -d. -f2 | base64 -d | jq -r '.exp' | xargs -I {} date -r {}
   ```

3. Verify token has required scopes:
   ```bash
   # Check "scp" or "roles" claim
   echo "$TOKEN" | cut -d. -f2 | base64 -d | jq -r '.scp // .roles'
   ```

4. Enable debug logging:
   ```bash
   # In .env
   DEBUG_MODE=true
   LOG_LEVEL=DEBUG
   LOG_JWT_CLAIMS=true

   # Restart and check logs
   docker-compose restart mcp-server
   docker-compose logs -f mcp-server
   ```

## Next Steps

1. **Set up Entra ID** - If you haven't already, follow [docs/setup/entra-id-setup.md](./docs/setup/entra-id-setup.md)
2. **Test all flows** - Try public client, confidential client, and service principal flows
3. **Integrate with MCP clients** - Connect VS Code, Claude Desktop, or custom clients
4. **Deploy to production** - Follow deployment guides in `docs/setup/`

## Stopping the Server

```bash
# Stop server
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Getting Help

- Check logs: `docker-compose logs -f mcp-server`
- Enable debug mode: Set `DEBUG_MODE=true` in `.env`
- Review documentation: [CLAUDE.md](./CLAUDE.md) and [docs/](./docs/)
- Check Swagger UI: http://localhost:8000/docs

## Security Reminder

Before deploying to production:

- [ ] Disable `DEBUG_MODE`
- [ ] Disable `ENABLE_MOCK_AUTH`
- [ ] Disable `LOG_JWT_CLAIMS`
- [ ] Enable `ENFORCE_HTTPS_REDIRECTS`
- [ ] Set appropriate `CORS_ALLOWED_ORIGINS`
- [ ] Review all security settings in `.env`

Enjoy your MCP server with proper enterprise authentication! 🎉
