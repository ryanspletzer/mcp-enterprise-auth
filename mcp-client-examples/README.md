# MCP Client Examples

This directory contains example MCP clients demonstrating all OAuth flows supported by the MCP server with proper enterprise authentication.

## Overview

Each example demonstrates a different OAuth 2.0 / OpenID Connect flow with Entra ID (Azure AD):

| Client | Flow | User Interaction | Use Case |
|--------|------|------------------|----------|
| **public-client-no-creds** | DCR + Auth Code + PKCE | Required | Generic clients without pre-registration |
| **public-client-with-creds** | Auth Code + PKCE | Required | Known clients (desktop/mobile apps) |
| **confidential-client** | Auth Code + PKCE + Secret | Required | Backend/server applications |
| **service-principal** | Client Credentials | Not required | Automation/machine-to-machine |

## Quick Start

### Prerequisites

- Python 3.11+
- MCP server running (see main [README.md](../README.md))
- Entra ID tenant with app registrations configured

### Choose Your Client

**For interactive user authentication:**

```bash
# Option 1: No credentials (uses DCR)
cd public-client-no-creds
python client.py

# Option 2: With pre-configured client_id
cd public-client-with-creds
python client.py

# Option 3: With client_id and client_secret (backend)
cd confidential-client
python client.py
```text

**For automated/headless scenarios:**

```bash
cd service-principal
python client.py
```

## Client Comparison

### 1. Public Client (No Credentials)

**Directory:** `public-client-no-creds/`

**When to use:**

- Generic/unknown clients
- Don't want to pre-register each client
- Testing DCR emulation
- Prototype/proof-of-concept

**OAuth Flow:**

1. Client calls MCP server's `/dcr/register` endpoint
2. Server detects client type and returns pre-registered `client_id`
3. Client performs Authorization Code + PKCE flow
4. Client exchanges code for token
5. Client calls MCP API with token

**Configuration needed:**

- MCP server URL
- Redirect URI (default: `http://localhost:8080/callback`)

**Security:**

- ✅ PKCE protects against code interception
- ✅ No secrets (public client)
- ⚠️ Relies on server-side client detection

[Full documentation →](./public-client-no-creds/README.md)

---

### 2. Public Client (With Credentials)

**Directory:** `public-client-with-creds/`

**When to use:**

- Desktop applications
- Mobile applications
- Single-page applications (SPA)
- Known/registered clients

**OAuth Flow:**

1. Client has pre-configured `client_id`
2. Client performs Authorization Code + PKCE flow
3. Client exchanges code for token (no DCR needed)
4. Client calls MCP API with token

**Configuration needed:**

- Client ID (from Entra ID)
- Tenant ID
- MCP server URL
- Redirect URI

**Security:**

- ✅ PKCE protects against code interception
- ✅ State parameter for CSRF protection
- ✅ No secrets (public client)
- ✅ Standard OAuth flow

[Full documentation →](./public-client-with-creds/README.md)

---

### 3. Confidential Client

**Directory:** `confidential-client/`

**When to use:**

- Backend web applications
- Server-side applications
- Applications that can securely store secrets

**OAuth Flow:**

1. Client has pre-configured `client_id` and `client_secret`
2. Client performs Authorization Code + PKCE flow
3. Client exchanges code for token WITH client authentication
4. Client calls MCP API with token

**Configuration needed:**

- Client ID (from Entra ID)
- Client Secret (from Entra ID)
- Tenant ID
- MCP server URL
- Redirect URI

**Security:**

- ✅ Client secret authenticates the client
- ✅ PKCE adds defense in depth
- ✅ State parameter for CSRF protection
- ✅ Higher trust level than public clients
- ⚠️ Must securely store client_secret

[Full documentation →](./confidential-client/README.md)

---

### 4. Service Principal (Client Credentials)

**Directory:** `service-principal/`

**When to use:**

- Automation/scheduled tasks
- CI/CD pipelines
- Background jobs
- Machine-to-machine communication
- No user interaction possible

**OAuth Flow:**

1. Client has service principal credentials (`client_id` + `client_secret`)
2. Client requests app-only token via Client Credentials flow
3. Client calls MCP API with app-only token (no user context)

**Configuration needed:**

- Client ID (service principal)
- Client Secret (service principal)
- Tenant ID
- MCP server URL

**Security:**

- ✅ No user interaction required
- ✅ App-only permissions (application roles)
- ✅ Suitable for trusted environments
- ⚠️ Must securely store client_secret
- ⚠️ Higher privileges (use least privilege principle)

[Full documentation →](./service-principal/README.md)

## Setup Instructions

### 1. Install Dependencies

Each client has its own `requirements.txt`:

```bash
cd <client-directory>
pip install -r requirements.txt
```

Or install for all clients:

```bash
for dir in public-client-no-creds public-client-with-creds confidential-client service-principal; do
    pip install -r $dir/requirements.txt
done
```

### 2. Configure Environment

Each client has `.env.example`:

```bash
cd <client-directory>
cp .env.example .env
# Edit .env with your Entra ID configuration
```

### 3. Run Client

```bash
python client.py
```

## Entra ID Configuration

Each client type requires specific Entra ID configuration. See the [Entra ID Setup Guide](../docs/setup/entra-id-setup.md) for detailed instructions.

### Quick Reference

| Client Type | App Type | Client Secret? | Redirect URI? | Permissions |
| ----------- | -------- | -------------- | ------------- | ----------- |
| public-client-no-credentials | Public | No | Yes | Delegated |
| public-client-with-credentials | Public | No | Yes | Delegated |
| confidential-client | Confidential | Yes | Yes | Delegated |
| service-principal | Confidential | Yes | No | Application |

## Running with Docker

Each client includes a Dockerfile:

```bash
# Build client image
cd <client-directory>
docker build -t mcp-client-<type> .

# Run with environment variables
docker run --rm \
  -e CLIENT_ID=... \
  -e TENANT_ID=... \
  -e MCP_SERVER_URL=http://host.docker.internal:8000 \
  mcp-client-<type>
```

## Docker Compose

Run all clients together:

```bash
# From mcp-client-examples directory
docker-compose up
```

See [docker-compose.yml](./docker-compose.yml) for configuration.

## Flow Decision Tree

```text
Need to authenticate with MCP server?
│
├─ YES, with user context (delegated permissions)
│  │
│  ├─ Do you have a pre-registered client_id?
│  │  │
│  │  ├─ NO
│  │  │  └─> Use: public-client-no-creds (DCR flow)
│  │  │
│  │  └─ YES
│  │     │
│  │     ├─ Can you securely store a client_secret?
│  │     │  │
│  │     │  ├─ NO (browser/mobile/desktop)
│  │     │  │  └─> Use: public-client-with-creds
│  │     │  │
│  │     │  └─ YES (backend/server)
│  │     │     └─> Use: confidential-client
│  │     │
│  │
└─ NO, machine-to-machine (no user)
   └─> Use: service-principal (Client Credentials)
```

## Token Types

### User Tokens (Delegated)

**Flows:** Authorization Code + PKCE
**Clients:** public-client-*, confidential-client
**Claims:**

- `scp` - Delegated scopes (e.g., "mcp.read mcp.write")
- `oid` - User object ID
- `upn` - User principal name
- `name` - User display name

**Use when:** Operating on behalf of a user

### App-Only Tokens

**Flow:** Client Credentials
**Client:** service-principal
**Claims:**

- `roles` - Application roles (e.g., ["MCP.ReadWrite.All"])
- `appid` - Application ID
- `idtyp: "app"` - Indicates app-only token
- No user-specific claims

**Use when:** Operating as the application itself

## Testing

### Test DCR Emulation

```bash
cd public-client-no-creds
python client.py
# Should auto-detect client type and return appropriate client_id
```

### Test Authorization Code Flow

```bash
cd public-client-with-creds
python client.py
# Browser should open for user login
# Should receive access token after login
```

### Test Client Credentials Flow

```bash
cd service-principal
python client.py
# Should acquire app-only token without user interaction
```

## Troubleshooting

### Common Issues

**"Invalid redirect_uri"**

- Ensure redirect URI in `.env` matches Entra ID registration exactly
- Check for trailing slashes, http vs https

**"PKCE validation failed"**

- Verify `code_verifier` is correctly generated
- Ensure `code_challenge_method` is "S256"

**"Insufficient privileges"**

- For user tokens: Check delegated permissions and user consent
- For app tokens: Check application permissions and admin consent

**"Invalid client"**

- Verify `CLIENT_ID` and `TENANT_ID` are correct
- Check that app registration exists in the tenant

### Enable Debug Logging

```python
# Add to client.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Best Practices

### All Clients

- ✅ Never commit `.env` files with real credentials
- ✅ Use HTTPS in production
- ✅ Validate all tokens server-side
- ✅ Implement token refresh before expiration
- ✅ Handle errors gracefully

### Public Clients

- ✅ Always use PKCE
- ✅ Validate state parameter
- ✅ Use local redirect URIs for desktop apps
- ⚠️ Cannot securely store secrets

### Confidential Clients & Service Principals

- ✅ Store secrets securely (Key Vault, environment variables, not code)
- ✅ Rotate secrets regularly
- ✅ Use managed identities when possible (Azure)
- ✅ Apply least privilege principle
- ✅ Monitor and audit usage

## Development Workflow

### 1. Start MCP Server

```bash
cd ../mcp-server
make run
```

### 2. Choose Client Type

Based on your scenario (see decision tree above)

### 3. Configure Client

```bash
cd <client-directory>
cp .env.example .env
# Edit .env
```

### 4. Run Client

```bash
python client.py
```

### 5. Verify Flow

Check logs for:

- Token acquisition
- API calls
- Responses

## Next Steps

- Add token caching and refresh logic
- Implement retry and error handling
- Add request/response logging
- Support for additional MCP endpoints
- Add monitoring and alerting
- Implement rate limiting

## Resources

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [Microsoft Identity Platform Docs](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Main Project README](../README.md)
- [Entra ID Setup Guide](../docs/setup/entra-id-setup.md)

## Support

For issues or questions:

1. Check client-specific README in each directory
2. Review [troubleshooting section](../README.md#troubleshooting) in main README
3. Check MCP server logs for validation errors
4. Open an issue in the repository

---

**Happy authenticating!** 🔐
