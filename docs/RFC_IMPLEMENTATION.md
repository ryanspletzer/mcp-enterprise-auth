# RFC Implementation Guide

This document describes the OAuth 2.0 and OpenID Connect RFCs implemented in this project.

## Overview

This implementation provides a comprehensive OAuth 2.0/OIDC infrastructure with:

- **Mock Entra ID Provider** - Full OAuth 2.0 Authorization Server
- **MCP Server** - OAuth 2.0 Protected Resource Server with MCP protocol support
- **DCR Emulation** - Intelligent client detection for Dynamic Client Registration

## Implemented RFCs

### RFC 8414 - OAuth 2.0 Authorization Server Metadata

**Status:** Fully Implemented

**Endpoints:**

- `GET /.well-known/openid-configuration` (Primary)
- `GET /.well-known/oauth-authorization-server` (Alternative)

**Location:** `src/mock-entra-idp/app/endpoints/discovery.py`

**Metadata Provided:**

```json
{
  "issuer": "http://mock-idp:8001/v2.0",
  "authorization_endpoint": "http://mock-idp:8001/oauth2/v2.0/authorize",
  "token_endpoint": "http://mock-idp:8001/oauth2/v2.0/token",
  "jwks_uri": "http://mock-idp:8001/discovery/v2.0/keys",
  "response_types_supported": ["code"],
  "response_modes_supported": ["query", "fragment", "form_post"],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token",
    "client_credentials"
  ],
  "subject_types_supported": ["pairwise"],
  "id_token_signing_alg_values_supported": ["RS256"],
  "token_endpoint_auth_methods_supported": [
    "client_secret_post",
    "client_secret_basic",
    "none"
  ],
  "code_challenge_methods_supported": ["plain", "S256"],
  "scopes_supported": [
    "openid",
    "profile",
    "email",
    "offline_access"
  ],
  "registration_endpoint": null,
  "service_documentation": null,
  "ui_locales_supported": ["en-US"]
}
```

**Purpose:**

Provides discovery metadata that allows clients to:

- Discover OAuth/OIDC endpoints dynamically
- Understand supported grant types and authentication methods
- Obtain JWKS URI for token validation
- Determine supported scopes and response types

**Testing:**

```bash
# Test OIDC discovery endpoint
curl http://localhost:8001/.well-known/openid-configuration | jq

# Test OAuth AS metadata endpoint
curl http://localhost:8001/.well-known/oauth-authorization-server | jq
```

---

### RFC 7591 - OAuth 2.0 Dynamic Client Registration Protocol

**Status:** Implemented (Emulation Mode)

**Endpoint:** `POST /dcr/register`

**Location:** `src/mcp-server/app/dcr/endpoints.py`

**Implementation:** Emulated DCR with intelligent client detection

**Request Format:**

```json
{
  "redirect_uris": ["vscode://mcp-auth/callback"],
  "client_name": "VS Code MCP Client",
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

**Response Format:**

```json
{
  "client_id": "12345678-1234-1234-1234-123456789abc",
  "client_name": "VS Code MCP Client",
  "client_type": "public",
  "redirect_uris": ["vscode://mcp-auth/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none",
  "confidence": 0.95,
  "authorization_endpoint": "https://login.microsoftonline.com/.../oauth2/v2.0/authorize",
  "token_endpoint": "https://login.microsoftonline.com/.../oauth2/v2.0/token",
  "issuer": "https://login.microsoftonline.com/.../v2.0",
  "jwks_uri": "https://login.microsoftonline.com/.../discovery/v2.0/keys"
}
```

**Client Detection Strategy:**

1. **Priority 1: Redirect URI Matching** (Confidence: 0.95)
   - `vscode://` -> VS Code
   - `claude-desktop://` -> Claude Desktop
   - `claude-code://` -> Claude Code
   - `chatgpt://` -> ChatGPT

2. **Priority 2: User-Agent Matching** (Confidence: 0.85)
   - Header: `User-Agent: VSCode-MCP/1.0`
   - Header: `User-Agent: Claude-Desktop/1.0`

3. **Priority 3: Client Name Matching** (Confidence: 0.75)
   - `client_name`: "VS Code", "Claude Desktop", etc.

4. **Fallback: Generic Client** (Confidence: 0.50)
   - Returns generic MCP client credentials

**Purpose:**

Provides DCR-compatible client registration while:

- Leveraging pre-registered Entra ID clients
- Maintaining security through client detection
- Supporting credential-less public clients
- Providing OAuth endpoint discovery

**Testing:**

```bash
# Test DCR with VS Code client
curl -X POST http://localhost:8000/dcr/register \
  -H "Content-Type: application/json" \
  -H "User-Agent: VSCode-MCP/1.0" \
  -d '{
    "redirect_uris": ["vscode://mcp-auth/callback"],
    "client_name": "VS Code MCP Client"
  }' | jq
```

---

### RFC 9728 - OAuth 2.0 Protected Resource Metadata

**Status:** Fully Implemented

**Endpoint:** `GET /.well-known/oauth-protected-resource`

**Location:** `src/mcp-server/app/discovery/endpoints.py`

**Metadata Provided:**

```json
{
  "resource": "api://mcp-server",
  "authorization_servers": [
    "https://login.microsoftonline.com/tenant-id"
  ],
  "bearer_methods_supported": ["header"],
  "scopes_supported": [
    "api://mcp-server/.default",
    "api://mcp-server/mcp.read",
    "api://mcp-server/mcp.write"
  ],
  "resource_signing_alg_values_supported": ["RS256"],
  "capabilities": {
    "mcp_protocol": "2024-11-05",
    "dcr_emulation": true,
    "pkce_required": true,
    "grant_types_supported": [
      "authorization_code",
      "client_credentials"
    ],
    "token_types_supported": ["user", "app"]
  },
  "mcp": {
    "version": "1.0.0",
    "endpoints": {
      "initialize": "http://localhost:8000/mcp/initialize",
      "tools_list": "http://localhost:8000/mcp/tools/list",
      "tools_call": "http://localhost:8000/mcp/tools/call",
      "resources_list": "http://localhost:8000/mcp/resources/list",
      "resources_read": "http://localhost:8000/mcp/resources/read",
      "prompts_list": "http://localhost:8000/mcp/prompts/list",
      "prompts_get": "http://localhost:8000/mcp/prompts/get"
    },
    "dcr_endpoint": "http://localhost:8000/dcr/register"
  },
  "permissions": {
    "read": {
      "delegated_scopes": ["api://mcp-server/mcp.read"],
      "application_roles": ["MCP.Read.All"]
    },
    "write": {
      "delegated_scopes": ["api://mcp-server/mcp.write"],
      "application_roles": ["MCP.ReadWrite.All"]
    }
  }
}
```

**Purpose:**

Advertises resource server capabilities including:

- Resource server identifier
- Supported authorization servers
- Token delivery methods (header, body, query)
- Available scopes and permissions
- MCP protocol endpoints
- DCR emulation capabilities

**Additional Custom Endpoint:**

`GET /.well-known/mcp-server` - Combined OAuth + MCP metadata

**Testing:**

```bash
# Test protected resource metadata
curl http://localhost:8000/.well-known/oauth-protected-resource | jq

# Test MCP server metadata
curl http://localhost:8000/.well-known/mcp-server | jq
```

---

## Additional OAuth 2.0 Implementations

### Authorization Code Flow with PKCE (RFC 7636)

**Status:** Fully Implemented

**Endpoints:**

- `GET /oauth2/v2.0/authorize` - Authorization request
- `POST /oauth2/v2.0/token` - Token exchange

**PKCE Support:**

- Code challenge methods: `plain`, `S256`
- Validates code_verifier against code_challenge
- Required for public clients

**Testing:**

```bash
# Generate PKCE challenge
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d /=+ | cut -c -43)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | base64 -w 0 | tr -d /=+ | cut -c -43)

# Start authorization flow
curl "http://localhost:8001/oauth2/v2.0/authorize?client_id=$CLIENT_ID&redirect_uri=http://localhost/callback&response_type=code&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256"
```

---

### Client Credentials Grant (RFC 6749 Section 4.4)

**Status:** Fully Implemented

**Endpoint:** `POST /oauth2/v2.0/token`

**Grant Type:** `client_credentials`

**Request:**

```bash
curl -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "scope=api://mcp-server/.default"
```

**Response:**

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "api://mcp-server/.default"
}
```

---

### Refresh Token Grant (RFC 6749 Section 6)

**Status:** Fully Implemented

**Endpoint:** `POST /oauth2/v2.0/token`

**Grant Type:** `refresh_token`

**Request:**

```bash
curl -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN" \
  -d "client_id=$CLIENT_ID"
```

---

## JWT Token Validation (RFC 7519)

**Status:** Fully Implemented

**Location:** `src/mcp-server/app/auth/jwt_validator.py`

**Validations Performed:**

1. **Signature Verification** - RS256 with JWKS
2. **Expiration** (`exp`) - Token not expired
3. **Not Before** (`nbf`) - Token is valid now
4. **Issued At** (`iat`) - Token not too old
5. **Audience** (`aud`) - Matches MCP server app ID
6. **Issuer** (`iss`) - Matches Entra ID tenant
7. **Tenant** (`tid`) - Matches allowed tenant(s)
8. **Token Version** (`ver`) - v2.0 tokens only
9. **Token Type** (`idtyp`) - Distinguishes user vs app tokens
10. **Scopes/Roles** - Validates `scp` or `roles` claims

---

## JWKS Endpoint (RFC 7517)

**Status:** Fully Implemented

**Endpoint:** `GET /discovery/v2.0/keys`

**Location:** `src/mock-entra-idp/app/endpoints/discovery.py`

**Response Format:**

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "key-id-1",
      "n": "modulus...",
      "e": "AQAB",
      "alg": "RS256"
    }
  ]
}
```

---

## Architecture Overview

```text
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│  MCP Clients    │         │   MCP Server     │         │  Mock Entra │
│  (VS Code,      │────1───▶│  (Resource       │────2───▶│  IdP        │
│   Claude, etc.) │         │   Server)        │         │             │
└─────────────────┘         └──────────────────┘         └─────────────┘
        │                            │                            │
        │    3. Discover endpoints   │                            │
        │◀───────────────────────────┘                            │
        │                                                          │
        │    4. Authorization Request (PKCE)                      │
        │─────────────────────────────────────────────────────────▶
        │                                                          │
        │    5. User Login & Consent                              │
        │◀─────────────────────────────────────────────────────────
        │                                                          │
        │    6. Authorization Code                                │
        │◀─────────────────────────────────────────────────────────
        │                                                          │
        │    7. Token Exchange (with code_verifier)               │
        │─────────────────────────────────────────────────────────▶
        │                                                          │
        │    8. Access Token + Refresh Token                      │
        │◀─────────────────────────────────────────────────────────
        │                                                          │
        │    9. Call MCP endpoint with Bearer token               │
        │────────────────────────────▶                             │
        │                             │                            │
        │                             │ 10. Validate JWT          │
        │                             │ (verify signature,        │
        │                             │  check claims)            │
        │                             │                            │
        │    11. MCP Response         │                            │
        │◀────────────────────────────┘                            │
        │                                                          │

Flow Steps:
1. Client performs DCR (RFC 7591) to get client_id
2. MCP server returns OAuth endpoints from RFC 8414 metadata
3. Client discovers authorization server endpoints
4. Client initiates OAuth flow with PKCE (RFC 7636)
5. User authenticates via mock Entra ID
6. Authorization code returned to client
7. Client exchanges code for tokens (validates PKCE)
8. Access token and refresh token issued
9. Client calls MCP endpoints with Bearer token
10. MCP server validates JWT (RFC 7519)
11. MCP server returns requested resources
```

---

## Discovery Flow

```text
┌─────────────────┐
│  New MCP Client │
└────────┬────────┘
         │
         │ 1. Discover MCP Server
         │    GET /.well-known/mcp-server
         │    (RFC 9728 + MCP metadata)
         ▼
┌─────────────────────────┐
│  MCP Server Metadata    │
│  - Resource identifier  │
│  - Auth server URL      │
│  - DCR endpoint         │
│  - MCP endpoints        │
│  - Required scopes      │
└────────┬────────────────┘
         │
         │ 2. Perform DCR
         │    POST /dcr/register
         │    (RFC 7591 emulation)
         ▼
┌─────────────────────────┐
│  Client Credentials     │
│  - client_id            │
│  - OAuth endpoints      │
│  - Confidence score     │
└────────┬────────────────┘
         │
         │ 3. Discover Auth Server
         │    GET /.well-known/openid-configuration
         │    (RFC 8414)
         ▼
┌─────────────────────────┐
│  Auth Server Metadata   │
│  - authorize_endpoint   │
│  - token_endpoint       │
│  - jwks_uri             │
│  - Supported flows      │
└────────┬────────────────┘
         │
         │ 4. Start OAuth Flow
         │    (PKCE, Authorization Code)
         ▼
┌─────────────────────────┐
│  Access Token           │
│  - JWT with claims      │
│  - Valid for MCP server │
└─────────────────────────┘
```

---

## Testing All RFCs

```bash
# 1. Test RFC 8414 - Authorization Server Metadata
curl http://localhost:8001/.well-known/openid-configuration | jq

# 2. Test RFC 9728 - Protected Resource Metadata
curl http://localhost:8000/.well-known/oauth-protected-resource | jq

# 3. Test RFC 7591 - Dynamic Client Registration
curl -X POST http://localhost:8000/dcr/register \
  -H "Content-Type: application/json" \
  -d '{
    "redirect_uris": ["http://localhost/callback"],
    "client_name": "Test Client"
  }' | jq

# 4. Test JWKS Endpoint (RFC 7517)
curl http://localhost:8001/discovery/v2.0/keys | jq

# 5. Test complete OAuth flow (see demos/guided-demo/demo.sh)
cd demos/guided-demo
./demo.sh
```

---

## Compliance Summary

| RFC | Title | Status | Endpoints | Notes |
|-----|-------|--------|-----------|-------|
| RFC 8414 | Authorization Server Metadata | Complete | `/.well-known/openid-configuration`, `/.well-known/oauth-authorization-server` | Full discovery support |
| RFC 7591 | Dynamic Client Registration | Emulated | `/dcr/register` | Intelligent client detection |
| RFC 9728 | Protected Resource Metadata | Complete | `/.well-known/oauth-protected-resource`, `/.well-known/mcp-server` | Full resource server metadata |
| RFC 6749 | OAuth 2.0 Framework | Complete | `/oauth2/v2.0/authorize`, `/oauth2/v2.0/token` | Authorization Code, Client Credentials, Refresh Token |
| RFC 7636 | PKCE | Complete | Token endpoint validates PKCE | S256 and plain methods |
| RFC 7519 | JWT | Complete | JWT validation in MCP server | RS256, full claim validation |
| RFC 7517 | JWK | Complete | `/discovery/v2.0/keys` | Public key distribution |

---

## References

- [RFC 8414 - OAuth 2.0 Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)
- [RFC 7591 - OAuth 2.0 Dynamic Client Registration Protocol](https://datatracker.ietf.org/doc/html/rfc7591)
- [RFC 9728 - OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728)
- [RFC 6749 - The OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)
- [RFC 7636 - Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636)
- [RFC 7519 - JSON Web Token (JWT)](https://datatracker.ietf.org/doc/html/rfc7519)
- [RFC 7517 - JSON Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517)
- [Microsoft Entra ID v2.0 Tokens](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols)
