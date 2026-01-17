# MCP Public Client - No Credentials (DCR Flow)

This example demonstrates a **public client without pre-configured credentials** that uses the MCP server's DCR (Dynamic Client Registration) emulation to obtain OAuth credentials.

## Flow Overview

```
┌──────────┐                 ┌────────────┐                ┌──────────┐
│  Client  │                 │ MCP Server │                │ Entra ID │
└────┬─────┘                 └─────┬──────┘                └────┬─────┘
     │                             │                            │
     │ 1. POST /dcr/register       │                            │
     │─────────────────────────────>                            │
     │    (no client_id)            │                            │
     │                              │                            │
     │ 2. DCR Response              │                            │
     │<─────────────────────────────│                            │
     │    (client_id, endpoints)    │                            │
     │                              │                            │
     │ 3. Authorization Code + PKCE │                            │
     │────────────────────────────────────────────────────────────>
     │    (using client_id from DCR)│                            │
     │                              │                            │
     │ 4. Authorization Code        │                            │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 5. Exchange code for token   │                            │
     │────────────────────────────────────────────────────────────>
     │                              │                            │
     │ 6. Access Token              │                            │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 7. Call MCP API with token   │                            │
     │─────────────────────────────>│                            │
     │                              │ 8. Validate JWT            │
     │                              │────────────────────────────>
     │                              │                            │
     │                              │ 9. JWKS + validation       │
     │                              │<────────────────────────────
     │                              │                            │
     │ 10. MCP Response             │                            │
     │<─────────────────────────────│                            │
```

## Key Features

- ✅ **No pre-configured client_id** - Relies on DCR emulation
- ✅ **Client detection** - Server detects client type from redirect_uri/User-Agent
- ✅ **OAuth Authorization Code + PKCE** - Secure public client flow
- ✅ **Interactive browser flow** - Opens browser for user login
- ✅ **Local callback server** - Receives OAuth callback
- ✅ **Structured logging** - Clear visibility into each step

## Prerequisites

- Python 3.11+
- MCP server running (default: http://localhost:8000)
- Entra ID configured with appropriate app registrations

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run the Client

```bash
python client.py
```

## How It Works

### Step 1: DCR Registration

The client calls the MCP server's `/dcr/register` endpoint **without** providing a `client_id`. The server:

1. Examines the `redirect_uri` (e.g., `http://localhost:8080/callback`)
2. Checks the `User-Agent` header
3. Detects the client type (defaults to "Generic")
4. Returns the appropriate pre-registered `client_id` from Entra ID

**Request:**
```json
POST /dcr/register
{
  "redirect_uris": ["http://localhost:8080/callback"],
  "client_name": "Generic MCP Client (No Creds)",
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

**Response:**
```json
{
  "client_id": "12345678-1234-1234-1234-123456789abc",
  "authorization_endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
  "token_endpoint": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
  "require_pkce": true,
  ...
}
```

### Step 2: OAuth Authorization

The client uses the `client_id` from DCR to perform OAuth Authorization Code + PKCE flow:

1. Generates PKCE `code_verifier` and `code_challenge`
2. Builds authorization URL with all parameters
3. Opens browser for user to authenticate
4. Starts local HTTP server on port 8080
5. Receives authorization code via callback

### Step 3: Token Exchange

The client exchanges the authorization code for an access token:

```
POST {token_endpoint}
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&grant_type=authorization_code
&code={authorization_code}
&redirect_uri=http://localhost:8080/callback
&code_verifier={code_verifier}
```

### Step 4: MCP API Calls

The client makes authenticated requests to MCP endpoints:

```
GET /api/me
Authorization: Bearer {access_token}
```

The MCP server validates the JWT and returns user information.

## Example Output

```
2026-01-17T12:00:00 [info] client_starting mcp_server_url=http://localhost:8000
2026-01-17T12:00:00 [info] === Step 1: DCR Registration ===
2026-01-17T12:00:00 [info] dcr_registration_starting
2026-01-17T12:00:01 [info] dcr_registration_successful client_id=abc123...
2026-01-17T12:00:01 [info] === Step 2: OAuth Authorization ===
2026-01-17T12:00:01 [info] opening_browser_for_authorization
2026-01-17T12:00:01 [info] callback_server_started port=8080
2026-01-17T12:00:15 [info] authorization_code_received
2026-01-17T12:00:15 [info] exchanging_code_for_token
2026-01-17T12:00:16 [info] token_acquired expires_in=3599
2026-01-17T12:00:16 [info] === Step 3: MCP API Calls ===
2026-01-17T12:00:16 [info] calling_mcp_api endpoint=/health
2026-01-17T12:00:16 [info] health_check result={'status': 'healthy'}
2026-01-17T12:00:16 [info] calling_mcp_api endpoint=/api/me
2026-01-17T12:00:16 [info] current_user result={'token_type': 'user', ...}
2026-01-17T12:00:16 [info] === Client Flow Complete ===
```

## Running with Docker

```bash
# Build image
docker build -t mcp-client-no-creds .

# Run with environment variables
docker run --rm \
  -e MCP_SERVER_URL=http://host.docker.internal:8000 \
  -e REDIRECT_URI=http://localhost:8080/callback \
  -p 8080:8080 \
  mcp-client-no-creds
```

**Note:** Interactive browser flow may not work in Docker. Consider using network mode or running locally.

## Customization

### Change Client Detection

Modify the `user_agent` to trigger different client type detection:

```python
client = MCPPublicClient(
    mcp_server_url="http://localhost:8000",
    user_agent="VSCode-MCP/1.0",  # Will be detected as VS Code client
)
```

### Custom Scopes

Request specific scopes instead of `.default`:

```bash
export SCOPE="api://mcp-server/mcp.read api://mcp-server/mcp.write"
```

## Troubleshooting

### "DCR registration failed"

- Ensure MCP server is running and accessible
- Check that DCR endpoints are enabled in server configuration
- Verify redirect_uri is in the allowed list

### "Token exchange failed"

- Verify the client_id from DCR matches Entra ID registration
- Check that redirect_uri exactly matches the registered URI
- Ensure PKCE code_verifier is correctly generated

### Browser doesn't open

- Manually copy the authorization URL from logs
- Paste into browser
- Complete login flow
- Browser will redirect to http://localhost:8080/callback

### "Port 8080 already in use"

Change the redirect URI:

```bash
export REDIRECT_URI=http://localhost:9000/callback
```

And update the Entra ID app registration redirect URIs accordingly.

## Security Notes

- ✅ **PKCE required** - Protects against authorization code interception
- ✅ **Public client** - No client_secret (can't be kept secret in browser/desktop app)
- ✅ **Local redirect** - Callback to localhost only
- ⚠️ **User interaction required** - Not suitable for automated/headless scenarios
- ⚠️ **Token storage** - Access token is in memory only (not persisted)

## Next Steps

- Add refresh token support for long-lived sessions
- Implement token caching/persistence
- Add error recovery and retry logic
- Support multiple MCP API endpoints
- Add request/response logging

## Related Examples

- **public-client-with-creds** - Public client with pre-configured client_id (no DCR)
- **confidential-client** - Confidential client with client_secret
- **service-principal** - Service principal with Client Credentials flow (no user)
