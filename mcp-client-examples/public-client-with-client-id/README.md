# MCP Public Client - With Credentials (Auth Code + PKCE)

This example demonstrates a **public client with pre-configured credentials** that uses OAuth Authorization Code + PKCE flow to authenticate with Entra ID.

## Flow Overview

```text
┌──────────┐                 ┌────────────┐                ┌──────────┐
│  Client  │                 │ MCP Server │                │ Entra ID │
└────┬─────┘                 └─────┬──────┘                └────┬─────┘
     │                             │                            │
     │ 1. Authorization Code + PKCE                             │
     │────────────────────────────────────────────────────────────>
     │    (using pre-configured client_id)                      │
     │                              │                            │
     │ 2. User Login & Consent      │                            │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 3. Authorization Code        │                            │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 4. Exchange code for token   │                            │
     │────────────────────────────────────────────────────────────>
     │    (with PKCE code_verifier) │                            │
     │                              │                            │
     │ 5. Access Token + Refresh Token                           │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 6. Call MCP API with token   │                            │
     │─────────────────────────────>│                            │
     │                              │ 7. Validate JWT            │
     │                              │────────────────────────────>
     │                              │                            │
     │                              │ 8. JWKS + validation       │
     │                              │<────────────────────────────
     │                              │                            │
     │ 9. MCP Response              │                            │
     │<─────────────────────────────│                            │
```

## Key Features

- ✅ **Pre-configured client_id** - No DCR needed
- ✅ **OAuth Authorization Code + PKCE** - Industry standard flow
- ✅ **Refresh token support** - Long-lived sessions
- ✅ **State parameter validation** - CSRF protection
- ✅ **Interactive browser flow** - User authentication
- ✅ **Structured logging** - Clear visibility into each step

## Prerequisites

- Python 3.11+
- MCP server running (default: http://localhost:8000)
- Entra ID app registration (public client type)
- `CLIENT_ID` and `TENANT_ID` from Entra ID

## Entra ID Configuration

This client requires a **public client** app registration in Entra ID:

1. Go to Azure Portal → Entra ID → App registrations
2. Create new registration:
   - **Name**: "MCP Public Client"
   - **Supported account types**: Single tenant
   - **Redirect URI**: Web → `http://localhost:8080/callback`
3. Under **Authentication**:
   - Enable "Public client flows" → NO (use Auth Code flow)
   - Add redirect URI: `http://localhost:8080/callback`
4. Under **API permissions**:
   - Add permission → My APIs → "MCP Server"
   - Select delegated permissions: `mcp.read`, `mcp.write`
   - Grant admin consent
5. Copy **Application (client) ID** and **Directory (tenant) ID**

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

Required values:

```bash
CLIENT_ID=12345678-1234-1234-1234-123456789abc
TENANT_ID=87654321-4321-4321-4321-987654321cba
MCP_SERVER_URL=http://localhost:8000
REDIRECT_URI=http://localhost:8080/callback
SCOPE=api://mcp-server/.default
```

### 3. Run the Client

```bash
python client.py
```

## How It Works

### Step 1: PKCE Generation

The client generates a PKCE code verifier and challenge:

```python
# Generate 32 random bytes, base64 encode
code_verifier = urlsafe_b64encode(secrets.token_bytes(32))

# SHA256 hash the verifier
code_challenge = sha256(code_verifier).base64_encode()
```

### Step 2: Authorization Request

The client builds an authorization URL and opens the browser:

```text
https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?
  client_id={client_id}
  &response_type=code
  &redirect_uri=http://localhost:8080/callback
  &scope=api://mcp-server/.default
  &state={random_state}
  &code_challenge={code_challenge}
  &code_challenge_method=S256
```

### Step 3: User Authentication

The user:

1. Logs in with their Entra ID credentials
2. Consents to the requested permissions (if needed)
3. Is redirected back to `http://localhost:8080/callback?code=...&state=...`

### Step 4: Callback Handling

The client:

1. Starts a local HTTP server on port 8080
2. Receives the authorization code
3. Validates the state parameter (CSRF protection)
4. Extracts the authorization code

### Step 5: Token Exchange

The client exchanges the code for tokens:

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&grant_type=authorization_code
&code={authorization_code}
&redirect_uri=http://localhost:8080/callback
&code_verifier={code_verifier}
```

Response:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "0.AXAA...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

### Step 6: MCP API Calls

The client makes authenticated requests:

```http
GET /api/me
Authorization: Bearer {access_token}
```

### Step 7: Token Refresh (Optional)

When the access token expires, use the refresh token:

```python
await client.refresh_access_token()
```

## Example Output

```text
2026-01-17T12:00:00 [info] client_starting client_id=abc123... tenant_id=def456...
2026-01-17T12:00:00 [info] === Step 1: OAuth Authorization ===
2026-01-17T12:00:00 [info] authorization_flow_starting
2026-01-17T12:00:00 [info] pkce_generated code_challenge_method=S256
2026-01-17T12:00:00 [info] opening_browser_for_authorization
2026-01-17T12:00:00 [info] callback_server_started port=8080
2026-01-17T12:00:15 [info] authorization_code_received
2026-01-17T12:00:15 [info] exchanging_code_for_token
2026-01-17T12:00:16 [info] token_acquired expires_in=3599 has_refresh_token=True
2026-01-17T12:00:16 [info] === Step 2: MCP API Calls ===
2026-01-17T12:00:16 [info] calling_mcp_api endpoint=/health
2026-01-17T12:00:16 [info] health_check result={'status': 'healthy'}
2026-01-17T12:00:16 [info] calling_mcp_api endpoint=/api/me
2026-01-17T12:00:16 [info] current_user result={'token_type': 'user', ...}
2026-01-17T12:00:16 [info] === Client Flow Complete ===
```

## Running with Docker

```bash
# Build image
docker build -t mcp-client-with-creds .

# Run with environment variables
docker run --rm \
  -e CLIENT_ID=your-client-id \
  -e TENANT_ID=your-tenant-id \
  -e MCP_SERVER_URL=http://host.docker.internal:8000 \
  -e REDIRECT_URI=http://localhost:8080/callback \
  -p 8080:8080 \
  mcp-client-with-creds
```

## Advanced Usage

### Custom Scopes

Request specific scopes:

```bash
export SCOPE="api://mcp-server/mcp.read api://mcp-server/mcp.write"
```

### Refresh Token Flow

```python
# After initial authorization
client = MCPPublicClientWithCreds(...)
await client.authorize()

# Later, when token expires
await client.refresh_access_token()

# Make API calls with new token
await client.call_mcp_api("/api/me")
```

### Error Handling

```python
try:
    await client.authorize()
except Exception as e:
    if "AADSTS50011" in str(e):
        # Redirect URI mismatch
        print("Check redirect_uri in Entra ID app registration")
    elif "AADSTS65001" in str(e):
        # User declined consent
        print("User must consent to requested permissions")
    else:
        raise
```

## Troubleshooting

### "Invalid redirect_uri"

Ensure the redirect URI in `.env` **exactly matches** the one registered in Entra ID:

- `http://localhost:8080/callback` ✅
- `http://localhost:8080/callback/` ❌ (trailing slash)
- `https://localhost:8080/callback` ❌ (https vs http)

### "Invalid client"

- Verify `CLIENT_ID` is correct
- Check that the app registration exists in the specified tenant
- Ensure the app is configured as a public client

### "State parameter mismatch"

This indicates a possible CSRF attack or callback handling issue:

- Check that the callback server is running
- Verify no proxy is modifying the callback URL
- Ensure browser cookies are enabled

### "Token exchange failed: invalid_grant"

Common causes:

- Authorization code already used (codes are single-use)
- Code expired (10 minute lifetime)
- `code_verifier` doesn't match `code_challenge`
- Redirect URI mismatch

### Browser doesn't open

Manually copy the authorization URL from logs:

```text
2026-01-17T12:00:00 [info] opening_browser_for_authorization
```

Paste into browser and complete the flow.

## Security Notes

- ✅ **PKCE required** - Mitigates authorization code interception
- ✅ **State parameter** - CSRF protection
- ✅ **Public client** - No client_secret (can't be kept secret)
- ✅ **Refresh tokens** - Long-lived sessions without re-authentication
- ⚠️ **Token storage** - Tokens are in memory only (consider secure storage for production)
- ⚠️ **Local redirect** - Works for localhost/desktop apps only

## Differences from public-client-without-client-id

| Feature | No Creds (DCR) | With Creds |
| ------- | -------------- | ---------- |
| **DCR call** | Required | Not needed |
| **client_id** | From DCR response | Pre-configured |
| **Setup** | Simpler (no Entra ID config) | Requires app registration |
| **Flexibility** | Server controls client_id | Client controls client_id |
| **Use case** | Generic/unknown clients | Known/registered clients |

## Next Steps

- Implement token caching/persistence
- Add automatic token refresh
- Support for multiple resource servers
- Implement logout flow
- Add token introspection

## Related Examples

- **public-client-without-client-id** - Public client using DCR (no pre-configured client_id)
- **confidential-client** - Confidential client with client_secret
- **service-principal** - Service principal with Client Credentials flow (no user)
