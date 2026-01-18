# MCP Confidential Client - Auth Code + PKCE + Client Secret

This example demonstrates a **confidential client** that uses OAuth Authorization Code + PKCE flow with client secret authentication.

## Flow Overview

```text
┌──────────┐                 ┌────────────┐                ┌──────────┐
│  Client  │                 │ MCP Server │                │ Entra ID │
└────┬─────┘                 └─────┬──────┘                └────┬─────┘
     │                             │                            │
     │ 1. Authorization Code + PKCE                             │
     │────────────────────────────────────────────────────────────>
     │    (client_id, no secret in URL)                         │
     │                              │                            │
     │ 2. User Login & Consent      │                            │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 3. Authorization Code        │                            │
     │<────────────────────────────────────────────────────────────
     │                              │                            │
     │ 4. Exchange code for token   │                            │
     │────────────────────────────────────────────────────────────>
     │    (client_id + client_secret + code_verifier)           │
     │                              │                            │
     │ 5. Validate client_secret    │                            │
     │                              │<────────────────────────────
     │                              │                            │
     │ 6. Access Token + Refresh Token                           │
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

- ✅ **Confidential client** - Can securely store client_secret
- ✅ **Client authentication** - Secret validates client identity
- ✅ **PKCE still used** - Defense in depth
- ✅ **Refresh token support** - Long-lived sessions
- ✅ **Higher security** - Suitable for backend/server applications
- ✅ **State parameter** - CSRF protection

## Prerequisites

- Python 3.11+
- MCP server running (default: http://localhost:8000)
- Entra ID app registration (confidential client type)
- `CLIENT_ID`, `CLIENT_SECRET`, and `TENANT_ID` from Entra ID

## Entra ID Configuration

This client requires a **confidential client** app registration in Entra ID:

1. Go to Azure Portal → Entra ID → App registrations
2. Create new registration:
   - **Name**: "MCP Confidential Client"
   - **Supported account types**: Single tenant
   - **Redirect URI**: Web → `http://localhost:8080/callback`
3. Under **Certificates & secrets**:
   - Click "New client secret"
   - Add description: "MCP Client Secret"
   - Choose expiration (e.g., 24 months)
   - **Copy the secret value** (you won't see it again!)
4. Under **Authentication**:
   - Add redirect URI: `http://localhost:8080/callback`
   - **Do NOT enable public client flows** (confidential client)
5. Under **API permissions**:
   - Add permission → My APIs → "MCP Server"
   - Select delegated permissions: `mcp.read`, `mcp.write`
   - Grant admin consent
6. Copy:
   - **Application (client) ID**
   - **Directory (tenant) ID**
   - **Client secret value**

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```text

Required values:
```bash
CLIENT_ID=12345678-1234-1234-1234-123456789abc
CLIENT_SECRET=abc~def123456789
TENANT_ID=87654321-4321-4321-4321-987654321cba
MCP_SERVER_URL=http://localhost:8000
REDIRECT_URI=http://localhost:8080/callback
SCOPE=api://mcp-server/.default
```

⚠️ **IMPORTANT**: Never commit `.env` with real secrets to version control!

### 3. Run the Client

```bash
python client.py
```

## How It Works

### Confidential vs Public Client

**Public Client:**
- Cannot securely store secrets (browser, mobile, desktop apps)
- Uses only PKCE for security
- Token request: `client_id` + `code_verifier`

**Confidential Client (This Example):**
- Can securely store secrets (backend servers, secure environments)
- Uses client_secret for authentication
- Token request: `client_id` + `client_secret` + `code_verifier`

### Step 1: Authorization Request

Same as public client - secret is NOT included in the authorization URL:

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

### Step 2: Token Exchange with Client Authentication

The client_secret is included in the token request (server-to-server):

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&client_secret={client_secret}     ← Client authentication
&grant_type=authorization_code
&code={authorization_code}
&redirect_uri=http://localhost:8080/callback
&code_verifier={code_verifier}     ← PKCE verification
```

Entra ID validates:
1. ✅ Client secret is correct
2. ✅ Code verifier matches code challenge
3. ✅ Authorization code is valid and not expired
4. ✅ Redirect URI matches

### Step 3: Token Response

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "0.AXAA...",
  "expires_in": 3599,
  "token_type": "Bearer",
  "scope": "api://mcp-server/.default"
}
```

### Step 4: Refresh Token with Client Authentication

Client secret is also required when refreshing:

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&client_secret={client_secret}     ← Required for confidential clients
&grant_type=refresh_token
&refresh_token={refresh_token}
```

## Example Output

```text
2026-01-17T12:00:00 [info] client_starting client_id=abc123... client_type=confidential
2026-01-17T12:00:00 [info] === Step 1: OAuth Authorization ===
2026-01-17T12:00:00 [info] authorization_flow_starting
2026-01-17T12:00:00 [info] pkce_generated code_challenge_method=S256
2026-01-17T12:00:00 [info] opening_browser_for_authorization
2026-01-17T12:00:00 [info] callback_server_started port=8080
2026-01-17T12:00:15 [info] authorization_code_received
2026-01-17T12:00:15 [info] exchanging_code_for_token auth_method=client_secret_post
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
docker build -t mcp-confidential-client .

# Run with environment variables
docker run --rm \
  -e CLIENT_ID=your-client-id \
  -e CLIENT_SECRET=your-client-secret \
  -e TENANT_ID=your-tenant-id \
  -e MCP_SERVER_URL=http://host.docker.internal:8000 \
  -e REDIRECT_URI=http://localhost:8080/callback \
  -p 8080:8080 \
  mcp-confidential-client
```

⚠️ **Security**: Use Docker secrets or secret management for production!

```bash
# Using Docker secrets
echo "your-client-secret" | docker secret create mcp_client_secret -

docker run --rm \
  -e CLIENT_ID=your-client-id \
  -e CLIENT_SECRET_FILE=/run/secrets/mcp_client_secret \
  --secret mcp_client_secret \
  ...
```

## Security Best Practices

### ✅ DO

- **Store secrets securely**: Use environment variables, secret management systems, or secure vaults
- **Rotate secrets regularly**: Set expiration when creating client secrets
- **Use HTTPS in production**: Never send client_secret over HTTP
- **Limit secret exposure**: Only load secrets in secure environments
- **Use PKCE**: Even though you have a secret, PKCE adds defense in depth
- **Validate state parameter**: Prevents CSRF attacks
- **Log carefully**: Never log client_secret or access_tokens

### ❌ DON'T

- **Commit secrets to version control**: Use `.env.example` without real values
- **Embed secrets in code**: Always use configuration/environment
- **Share secrets**: Each environment should have unique credentials
- **Use client_secret in browser/mobile**: Only for backend/server applications
- **Ignore secret expiration**: Monitor and rotate before expiry

## Client Secret Management

### Creating Secret

```bash
# Azure CLI
az ad app credential reset \
  --id YOUR_CLIENT_ID \
  --append \
  --display-name "MCP Client Secret" \
  --years 2
```

### Rotating Secret

1. Create new secret in Entra ID
2. Update application configuration with new secret
3. Deploy and verify
4. Delete old secret after verification

### Secret Expiration

Set up monitoring for expiring secrets:

```python
# Check secret expiration (example)
from datetime import datetime, timedelta

SECRET_CREATED = datetime(2026, 1, 17)
SECRET_EXPIRES = SECRET_CREATED + timedelta(days=730)  # 2 years

days_until_expiry = (SECRET_EXPIRES - datetime.now()).days

if days_until_expiry < 30:
    logger.warning("client_secret_expiring_soon", days=days_until_expiry)
```

## Troubleshooting

### "Invalid client_secret"

- Verify the secret value is correct (no extra spaces)
- Check the secret hasn't expired
- Ensure you copied the secret value (not the secret ID)
- Create a new secret if the old one is lost

### "Unauthorized client"

- Verify the app registration is configured as a web/confidential client
- Check that "Allow public client flows" is **disabled**
- Ensure the client_id matches the app registration

### "PKCE validation failed"

Even with client_secret, PKCE is still validated:
- Ensure `code_verifier` is correctly generated
- Check that `code_challenge` matches the verifier
- Verify `code_challenge_method` is "S256"

## Comparison with Other Client Types

| Feature | Public Client | Confidential Client | Service Principal |
|---------|--------------|---------------------|-------------------|
| **User interaction** | Required | Required | Not required |
| **Client secret** | No | Yes | Yes |
| **PKCE** | Required | Recommended | Not used |
| **Token type** | User (delegated) | User (delegated) | App-only |
| **Use case** | Desktop/mobile | Backend/server | Automation |
| **Scopes** | Delegated | Delegated | Application |

## When to Use Confidential Client

✅ **Use confidential client when:**
- Running on a secure backend server
- Can securely store secrets (not browser/mobile)
- Need user context (delegated permissions)
- Want additional security layer beyond PKCE

❌ **Don't use confidential client for:**
- Browser-based applications (SPA)
- Mobile applications
- Desktop applications
- Any environment where secrets can be extracted

For those scenarios, use **public-client-with-creds** instead.

## Next Steps

- Implement secure secret storage (Azure Key Vault, HashiCorp Vault)
- Add secret rotation automation
- Implement certificate-based authentication (more secure than secrets)
- Add automatic token refresh before expiration
- Implement token caching

## Related Examples

- **public-client-no-creds** - Public client using DCR (no credentials)
- **public-client-with-creds** - Public client with client_id (no secret)
- **service-principal** - Service principal with Client Credentials flow (no user)
