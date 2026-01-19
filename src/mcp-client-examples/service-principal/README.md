# MCP Service Principal Client - Client Credentials Flow

This example demonstrates a **service principal** that uses OAuth Client Credentials flow
for machine-to-machine authentication **without user interaction**.

## Flow Overview

```text
+---------------+                 +-------------+                +-----------+
| Service       |                 | MCP Server  |                | Entra ID  |
| Principal     |                 |             |                |           |
+-------+-------+                 +------+------+                +-----+-----+
        |                                |                             |
        | 1. Client Credentials Request  |                             |
        |------------------------------------------------------------->|
        |    (client_id + client_secret + scope)                       |
        |                                |                             |
        | 2. Validate credentials        |                             |
        |                                |<----------------------------|
        |                                |                             |
        | 3. App-Only Access Token       |                             |
        |<-------------------------------------------------------------|
        |    (no user context, app permissions)                        |
        |                                |                             |
        | 4. Call MCP API with token     |                             |
        |------------------------------->|                             |
        |                                | 5. Validate JWT             |
        |                                |---------------------------->|
        |                                |                             |
        |                                | 6. JWKS + validation        |
        |                                |<----------------------------|
        |                                |    (check "roles" claim)    |
        |                                |                             |
        | 7. MCP Response                |                             |
        |<-------------------------------|                             |
        |                                |                             |
```

## Key Features

- **No user interaction** - Fully automated
- **App-only permissions** - Uses application roles, not delegated scopes
- **Client Credentials flow** - Standard OAuth 2.0 for machine-to-machine
- **Token caching** - Automatic token refresh before expiration
- **Service identity** - Authenticates as the application itself
- **Ideal for automation** - Background jobs, scheduled tasks, CI/CD

## Prerequisites

- Python 3.11+
- MCP server running (default: http://localhost:8000)
- Entra ID service principal with app registrations
- `CLIENT_ID`, `CLIENT_SECRET`, and `TENANT_ID` from Entra ID

## Entra ID Configuration

This client requires a **service principal** in Entra ID with **application permissions**:

### Step 1: Create App Registration

1. Go to Azure Portal -> Entra ID -> App registrations
2. Create new registration:
   - **Name**: "MCP Service Principal"
   - **Supported account types**: Single tenant
   - **Redirect URI**: None (not needed for Client Credentials)

### Step 2: Create Client Secret

1. Under **Certificates & secrets**:
   - Click "New client secret"
   - Add description: "MCP Automation Secret"
   - Choose expiration (e.g., 24 months)
   - **Copy the secret value** immediately!

### Step 3: Configure Application Permissions

1. Under **API permissions**:
   - Click "Add a permission"
   - Select "My APIs" -> "MCP Server"
   - Select **Application permissions** (NOT delegated):
     - `MCP.Read.All`
     - `MCP.ReadWrite.All`
   - Click "Add permissions"
2. **Grant admin consent** (required for application permissions)

### Step 4: Copy Configuration

Copy these values:

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
```

Required values:

```bash
CLIENT_ID=12345678-1234-1234-1234-123456789abc
CLIENT_SECRET=abc~def123456789
TENANT_ID=87654321-4321-4321-4321-987654321cba
MCP_SERVER_URL=http://localhost:8000
SCOPE=api://mcp-server/.default
```

**IMPORTANT**: Never commit secrets to version control!

### 3. Run the Client

```bash
python client.py
```

## How It Works

### Client Credentials vs Authorization Code

| Feature | Authorization Code | Client Credentials |
|---------|-------------------|-------------------|
| **User interaction** | Required | Not required |
| **User context** | Yes | No |
| **Token type** | User token | App-only token |
| **Permissions** | Delegated scopes | Application roles |
| **Use case** | On behalf of user | Machine-to-machine |
| **PKCE** | Required/Recommended | Not used |
| **Refresh token** | Yes | No (re-acquire instead) |

### Step 1: Token Request

The client sends credentials directly to the token endpoint:

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id={client_id}
&client_secret={client_secret}
&scope=api://mcp-server/.default
&grant_type=client_credentials
```

**No user involved** - this is direct machine-to-machine authentication.

### Step 2: Token Response

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3599,
  "ext_expires_in": 3599
}
```

**Note:** No refresh token - you re-acquire when the token expires.

### Step 3: Token Validation

The MCP server validates the JWT and checks:

1. Signature is valid (JWKS)
2. Token not expired
3. Audience matches (`api://mcp-server`)
4. Issuer is Entra ID
5. Token type is app-only (`idtyp: "app"` or no `scp` claim)
6. **Roles claim** contains required app permissions

**Key difference:** App-only tokens have `roles` claim, not `scp` claim.

### JWT Token Structure (App-Only)

```json
{
  "aud": "api://mcp-server",
  "iss": "https://login.microsoftonline.com/{tenant}/v2.0",
  "iat": 1705500000,
  "exp": 1705503599,
  "nbf": 1705500000,
  "aio": "...",
  "app_displayname": "MCP Service Principal",
  "appid": "12345678-1234-1234-1234-123456789abc",
  "idtyp": "app",
  "oid": "...",
  "roles": [
    "MCP.Read.All",
    "MCP.ReadWrite.All"
  ],
  "sub": "...",
  "tid": "87654321-4321-4321-4321-987654321cba",
  "uti": "...",
  "ver": "2.0"
}
```

**Key claims:**

- `idtyp: "app"` - Indicates app-only token
- `roles` - Application permissions (NOT `scp`)
- `appid` - Service principal app ID
- No user-specific claims (oid refers to app, not user)

## Example Output

```text
2026-01-17T12:00:00 [info] service_principal_starting flow_type=client_credentials
2026-01-17T12:00:00 [info] === Step 1: Acquire App-Only Token ===
2026-01-17T12:00:00 [info] acquiring_app_only_token grant_type=client_credentials
2026-01-17T12:00:01 [info] app_only_token_acquired expires_in=3599
2026-01-17T12:00:01 [info] === Step 2: MCP API Calls ===
2026-01-17T12:00:01 [info] calling_mcp_api endpoint=/health
2026-01-17T12:00:01 [info] health_check result={'status': 'healthy'}
2026-01-17T12:00:01 [info] calling_mcp_api endpoint=/api/me
2026-01-17T12:00:01 [info] service_principal_info result={'token_type': 'app_only', ...}
2026-01-17T12:00:01 [info] === Step 3: Demonstrate Token Management ===
2026-01-17T12:00:01 [info] using_cached_token time_until_expiry=3598
2026-01-17T12:00:01 [info] === Service Principal Flow Complete ===
```

## Running with Docker

```bash
# Build image
docker build -t mcp-service-principal .

# Run with environment variables
docker run --rm \
  -e CLIENT_ID=your-client-id \
  -e CLIENT_SECRET=your-client-secret \
  -e TENANT_ID=your-tenant-id \
  -e MCP_SERVER_URL=http://host.docker.internal:8000 \
  mcp-service-principal
```

### Production: Use Secrets

```bash
# Using Docker secrets
echo "your-client-secret" | docker secret create mcp_sp_secret -

docker service create \
  --name mcp-automation \
  --secret source=mcp_sp_secret,target=client_secret \
  -e CLIENT_ID=your-client-id \
  -e CLIENT_SECRET_FILE=/run/secrets/client_secret \
  -e TENANT_ID=your-tenant-id \
  mcp-service-principal
```

## Advanced Usage

### Automatic Token Refresh

The client automatically manages token lifecycle:

```python
client = MCPServicePrincipalClient(...)

# First call acquires token
await client.call_mcp_api("/api/me")

# Subsequent calls use cached token
await client.call_mcp_api("/api/data")

# Token auto-refreshes when expired
await asyncio.sleep(3700)  # Wait past expiration
await client.call_mcp_api("/api/me")  # Automatically gets new token
```

### Scheduled Background Jobs

```python
async def scheduled_task():
    """Run automated task every hour."""
    client = MCPServicePrincipalClient(...)

    while True:
        try:
            # Perform automated operations
            data = await client.call_mcp_api("/api/data")
            await process_data(data)

            logger.info("task_completed")
        except Exception as e:
            logger.error("task_failed", error=str(e))

        # Wait 1 hour
        await asyncio.sleep(3600)

# Run in background
asyncio.create_task(scheduled_task())
```

### CI/CD Integration

```yaml
# GitHub Actions example
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: Call MCP API
        env:
          CLIENT_ID: ${{ secrets.MCP_CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.MCP_CLIENT_SECRET }}
          TENANT_ID: ${{ secrets.MCP_TENANT_ID }}
        run: python mcp-client-examples/service-principal/client.py
```

## Security Best Practices

### DO

- **Use managed identities** when running on Azure (no secrets needed)
- **Rotate secrets regularly** - Set expiration and monitor
- **Use certificate authentication** instead of secrets (more secure)
- **Apply least privilege** - Only grant required application permissions
- **Secure secret storage** - Use Azure Key Vault, HashiCorp Vault, etc.
- **Monitor and audit** - Log all service principal activities
- **Separate environments** - Different credentials for dev/staging/prod

### DON'T

- **Commit secrets** to version control
- **Share secrets** across environments or applications
- **Grant excessive permissions** - Avoid broad "*.All" roles if possible
- **Ignore expiration** - Monitor secret lifetime
- **Log secrets** - Never log client_secret or tokens

## Managed Identity (Azure)

When running on Azure, use Managed Identity instead of client secrets:

```python
from azure.identity import DefaultAzureCredential

# No client_secret needed!
credential = DefaultAzureCredential()
token = credential.get_token("api://mcp-server/.default")

# Use token with MCP API
client = MCPServicePrincipalClient(...)
client.access_token = token.token
```

Benefits:

- No secrets to manage
- Automatic credential rotation
- Reduced security risk

## Certificate-Based Authentication

More secure than client secrets:

```python
# Using certificate instead of secret
from msal import ConfidentialClientApplication

app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential={
        "thumbprint": CERT_THUMBPRINT,
        "private_key": PRIVATE_KEY,
    },
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
)

token = app.acquire_token_for_client(scopes=[SCOPE])
```

## Troubleshooting

### "Insufficient privileges"

Service principal doesn't have required application permissions:

1. Check app registrations -> API permissions
2. Ensure **Application permissions** are added (not delegated)
3. Ensure admin consent is granted
4. Check MCP server requires the correct role

### "Invalid client"

- Verify CLIENT_ID and TENANT_ID are correct
- Ensure app registration exists in the tenant
- Check that client_secret hasn't expired

### "Unauthorized: Missing required role"

Token doesn't have required application role:

1. Check token claims: `roles` should contain required permissions
2. Verify admin consent was granted
3. Ensure MCP server is configured to accept the role

### Decode token to debug

```bash
# Extract token
TOKEN=$(curl -X POST ... | jq -r '.access_token')

# Decode JWT (without verification)
echo $TOKEN | cut -d. -f2 | base64 -d | jq

# Check claims
# - "idtyp": "app" indicates app-only token
# - "roles": [...] should contain required permissions
# - "aud": should match api://mcp-server
```

## Use Cases

**Perfect for:**

- Scheduled background jobs
- Automated data processing
- CI/CD pipelines
- System integration
- Monitoring and alerting
- Batch operations
- Inter-service communication

**Not suitable for:**

- User-facing applications
- Operations requiring user context
- Delegated permissions
- Scenarios needing user consent

## Comparison with Other Flows

| Scenario | Recommended Flow |
|----------|------------------|
| **User login required** | Public/Confidential Client (Auth Code) |
| **Desktop app** | Public Client with PKCE |
| **Web app backend** | Confidential Client |
| **Automation/CI/CD** | **Service Principal (This Example)** |
| **Azure VM/Function** | Managed Identity |

## Next Steps

- Implement managed identity for Azure deployments
- Add certificate-based authentication
- Implement comprehensive error handling and retry logic
- Add monitoring and alerting
- Set up secret rotation automation
- Implement rate limiting and throttling

## Related Examples

- **public-client-without-client-id** - Public client using DCR (user interaction)
- **public-client-with-client-id** - Public client with client_id (user interaction)
- **confidential-client** - Confidential client with secret (user interaction)
