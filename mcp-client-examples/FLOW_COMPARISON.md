# OAuth Flow Comparison

This document provides a detailed comparison of all OAuth flows implemented in the MCP client examples.

## Quick Reference Table

| Feature | Public (No Creds) | Public (With Creds) | Confidential | Service Principal |
|---------|-------------------|---------------------|--------------|-------------------|
| **Directory** | `public-client-no-creds/` | `public-client-with-creds/` | `confidential-client/` | `service-principal/` |
| **OAuth Flow** | Auth Code + PKCE | Auth Code + PKCE | Auth Code + PKCE | Client Credentials |
| **DCR Required** | Yes | No | No | No |
| **User Interaction** | Required | Required | Required | Not required |
| **Browser Opens** | Yes | Yes | Yes | No |
| **Client ID** | From DCR | Pre-configured | Pre-configured | Pre-configured |
| **Client Secret** | No | No | Yes | Yes |
| **PKCE** | Yes | Yes | Yes | No |
| **Token Type** | User (delegated) | User (delegated) | User (delegated) | App-only |
| **Permissions** | Delegated scopes | Delegated scopes | Delegated scopes | Application roles |
| **Refresh Token** | Yes | Yes | Yes | No (re-acquire) |
| **Token Claims** | `scp` (scopes) | `scp` (scopes) | `scp` (scopes) | `roles` (app roles) |
| **Use Case** | Generic/unknown clients | Known clients | Backend apps | Automation/M2M |
| **Complexity** | High | Medium | Medium | Low |
| **Security Level** | Medium | Medium | High | High |

## Detailed Flow Comparison

### 1. Public Client (No Credentials) - DCR Flow

```text
┌─────────┐         ┌────────────┐         ┌──────────┐
│ Client  │         │ MCP Server │         │ Entra ID │
└────┬────┘         └─────┬──────┘         └────┬─────┘
     │                    │                     │
     │ 1. DCR Register    │                     │
     │───────────────────>│                     │
     │                    │                     │
     │ 2. Client ID       │                     │
     │<───────────────────│                     │
     │                    │                     │
     │ 3. Auth Request (PKCE)                   │
     │─────────────────────────────────────────>│
     │                    │                     │
     │ 4. User Login      │                     │
     │<─────────────────────────────────────────│
     │                    │                     │
     │ 5. Auth Code       │                     │
     │<─────────────────────────────────────────│
     │                    │                     │
     │ 6. Token Exchange (code_verifier)        │
     │─────────────────────────────────────────>│
     │                    │                     │
     │ 7. Access Token    │                     │
     │<─────────────────────────────────────────│
     │                    │                     │
     │ 8. API Call        │                     │
     │───────────────────>│                     │
     │                    │ 9. Validate JWT     │
     │                    │────────────────────>│
     │                    │                     │
     │ 10. Response       │                     │
     │<───────────────────│                     │
```

**Steps:**

1. Client calls `/dcr/register` without client_id
2. Server detects client type, returns pre-registered client_id
3. Client initiates OAuth with PKCE
4. User authenticates via browser
5. Client receives authorization code
6. Client exchanges code for token (with PKCE)
7. Client receives access + refresh token

8-10. Client calls MCP API with validated token

**Unique Features:**

- ✨ No pre-configuration needed
- ✨ Server-side client detection
- ⚠️ Relies on DCR emulation accuracy

---

### 2. Public Client (With Credentials) - Standard Auth Code

```text
┌─────────┐                              ┌──────────┐
│ Client  │                              │ Entra ID │
└────┬────┘                              └────┬─────┘
     │                                        │
     │ 1. Auth Request (PKCE)                 │
     │───────────────────────────────────────>│
     │    client_id={pre-configured}          │
     │    code_challenge={PKCE}               │
     │                                        │
     │ 2. User Login                          │
     │<───────────────────────────────────────│
     │                                        │
     │ 3. Auth Code                           │
     │<───────────────────────────────────────│
     │                                        │
     │ 4. Token Exchange                      │
     │───────────────────────────────────────>│
     │    client_id={pre-configured}          │
     │    code_verifier={PKCE}                │
     │                                        │
     │ 5. Access Token + Refresh Token        │
     │<───────────────────────────────────────│
```

**Steps:**

1. Client initiates OAuth with pre-configured client_id
2. User authenticates via browser
3. Client receives authorization code
4. Client exchanges code for token (with PKCE)
5. Client receives access + refresh token

**Unique Features:**

- ✨ Standard OAuth 2.0 flow
- ✨ No server dependencies (DCR)
- ✨ Direct to Entra ID

---

### 3. Confidential Client - Auth Code with Client Authentication

```text
┌─────────┐                              ┌──────────┐
│ Client  │                              │ Entra ID │
└────┬────┘                              └────┬─────┘
     │                                        │
     │ 1. Auth Request (PKCE)                 │
     │───────────────────────────────────────>│
     │    client_id={pre-configured}          │
     │    code_challenge={PKCE}               │
     │    (no secret in URL)                  │
     │                                        │
     │ 2. User Login                          │
     │<───────────────────────────────────────│
     │                                        │
     │ 3. Auth Code                           │
     │<───────────────────────────────────────│
     │                                        │
     │ 4. Token Exchange + Client Auth        │
     │───────────────────────────────────────>│
     │    client_id={pre-configured}          │
     │    client_secret={secret}              │
     │    code_verifier={PKCE}                │
     │                                        │
     │ 5. Access Token + Refresh Token        │
     │<───────────────────────────────────────│
```

**Steps:**

1. Client initiates OAuth (secret NOT in URL)
2. User authenticates via browser
3. Client receives authorization code
4. Client exchanges code for token WITH client_secret
5. Client receives access + refresh token

**Unique Features:**

- ✨ Client authentication with secret
- ✨ Higher security than public clients
- ✨ PKCE + secret (defense in depth)
- ⚠️ Must securely store secret

---

### 4. Service Principal - Client Credentials

```text
┌─────────┐                              ┌──────────┐
│ Service │                              │ Entra ID │
│Principal│                              │          │
└────┬────┘                              └────┬─────┘
     │                                        │
     │ 1. Client Credentials Request          │
     │───────────────────────────────────────>│
     │    client_id={service-principal}       │
     │    client_secret={secret}              │
     │    scope=api://mcp-server/.default     │
     │    grant_type=client_credentials       │
     │                                        │
     │ 2. App-Only Access Token               │
     │<───────────────────────────────────────│
     │    (no refresh token)                  │
     │    (no user context)                   │
```

**Steps:**

1. Service principal sends credentials directly to token endpoint
2. Entra ID validates credentials
3. Service principal receives app-only access token

**Unique Features:**

- ✨ No user interaction
- ✨ No browser required
- ✨ App-only permissions
- ✨ Ideal for automation
- ⚠️ No refresh token (re-acquire when expired)

## Token Comparison

### User Token (Delegated Permissions)

**Flows:** Auth Code + PKCE (all three interactive clients)

**JWT Structure:**

```json
{
  "aud": "api://mcp-server",
  "iss": "https://login.microsoftonline.com/{tenant}/v2.0",
  "iat": 1705500000,
  "exp": 1705503599,
  "nbf": 1705500000,
  "scp": "mcp.read mcp.write",        ← Delegated scopes
  "name": "John Doe",
  "upn": "john.doe@example.com",
  "oid": "user-object-id",
  "tid": "tenant-id",
  "ver": "2.0"
}
```

**Key Claims:**

- `scp` - Space-separated scopes granted to user
- `oid` - User's object ID
- `upn` / `preferred_username` - User's principal name
- `name` - User's display name

**Validation:**

- Check `scp` claim contains required scopes
- Verify user identity from `oid` or `upn`

---

### App-Only Token (Application Permissions)

**Flow:** Client Credentials (service principal)

**JWT Structure:**

```json
{
  "aud": "api://mcp-server",
  "iss": "https://login.microsoftonline.com/{tenant}/v2.0",
  "iat": 1705500000,
  "exp": 1705503599,
  "nbf": 1705500000,
  "roles": [                           ← Application roles
    "MCP.Read.All",
    "MCP.ReadWrite.All"
  ],
  "appid": "service-principal-id",
  "idtyp": "app",                      ← Indicates app-only
  "oid": "service-principal-object-id",
  "tid": "tenant-id",
  "ver": "2.0"
}
```

**Key Claims:**

- `roles` - Array of application roles
- `appid` - Service principal's app ID
- `idtyp: "app"` - Indicates app-only token
- `oid` - Service principal's object ID (not user)
- **No `scp` claim** - Uses `roles` instead

**Validation:**

- Check `roles` claim contains required application permissions
- Verify `idtyp` is "app" or `scp` is absent
- Verify service principal identity from `appid`

## Security Comparison

### PKCE (Proof Key for Code Exchange)

**Used by:** Public clients, Confidential client
**Not used by:** Service Principal (Client Credentials flow)

**Purpose:** Protects against authorization code interception

**How it works:**

1. Generate random `code_verifier` (43-128 chars)
2. Create `code_challenge` = SHA256(code_verifier)
3. Send `code_challenge` in authorization request
4. Send `code_verifier` in token exchange
5. Server verifies SHA256(code_verifier) == code_challenge

**Security benefit:**

- Even if authorization code is intercepted, attacker needs `code_verifier`
- Mitigates authorization code interception attacks

---

### Client Authentication

**Used by:** Confidential client, Service Principal
**Not used by:** Public clients

**Method:** Client Secret (or Certificate)

**How it works:**

1. Client includes `client_secret` in token request
2. Entra ID validates secret matches registered value
3. Only proceeds if authentication succeeds

**Security benefit:**

- Proves client identity
- Prevents token theft if code is intercepted
- Higher trust level than public clients

---

### State Parameter

**Used by:** All interactive flows
**Not used by:** Client Credentials

**Purpose:** CSRF protection

**How it works:**

1. Generate random `state` value
2. Include in authorization request
3. Validate matches in callback
4. Reject if mismatch

**Security benefit:**

- Prevents CSRF attacks
- Ensures callback is from legitimate authorization request

## Use Case Decision Matrix

### Choose Public Client (No Creds) when

- ✅ Client type is unknown
- ✅ Testing/prototyping
- ✅ Don't want to pre-register
- ✅ Server supports DCR
- ❌ Production deployments (prefer pre-registered)

### Choose Public Client (With Creds) when

- ✅ Desktop application
- ✅ Mobile application
- ✅ Single-page application (SPA)
- ✅ Cannot securely store secrets
- ✅ Need user context
- ❌ Backend server (use confidential)

### Choose Confidential Client when

- ✅ Backend web application
- ✅ Server-side application
- ✅ Can securely store secrets
- ✅ Need user context
- ✅ Want higher security
- ❌ Browser/mobile (cannot secure secret)

### Choose Service Principal when

- ✅ Automation/scheduled tasks
- ✅ CI/CD pipelines
- ✅ Background jobs
- ✅ No user interaction possible
- ✅ Machine-to-machine
- ❌ Need user context (use Auth Code flow)

## Performance Comparison

| Metric | Public (No Creds) | Public (With Creds) | Confidential | Service Principal |
| ------ | ----------------- | ------------------- | ------------ | ----------------- |
| **Setup Time** | Low (no config) | Medium (config) | Medium (config + secret) | Medium (config + secret) |
| **Auth Time** | High (DCR + OAuth) | Medium (OAuth) | Medium (OAuth) | **Low (direct)** |
| **User Friction** | High (login) | High (login) | High (login) | **None** |
| **Token Refresh** | Automatic | Automatic | Automatic | Re-acquire |
| **Headless Support** | ❌ No | ❌ No | ❌ No | ✅ **Yes** |

## Error Scenarios Comparison

### Common Errors

| Error | Public (No Credentials) | Public (With Credentials) | Confidential | Service Principal |
| ----- | ----------------------- | ------------------------- | ------------ | ----------------- |
| **Invalid client_id** | From DCR response | Configuration error | Configuration error | Configuration error |
| **Invalid redirect_uri** | Yes | Yes | Yes | N/A |
| **PKCE failure** | Yes | Yes | Yes | N/A |
| **Invalid secret** | N/A | N/A | Yes | Yes |
| **User declined consent** | Yes | Yes | Yes | N/A |
| **Insufficient privileges** | Delegated | Delegated | Delegated | Application |

## Implementation Comparison

### Lines of Code

| Client | LOC | Complexity |
| ------ | --- | ---------- |
| public-client-no-creds | ~250 | High (DCR + OAuth) |
| public-client-with-creds | ~220 | Medium (OAuth) |
| confidential-client | ~230 | Medium (OAuth + secret) |
| service-principal | ~180 | **Low (direct token)** |

### Dependencies

All clients use:

- `httpx` - HTTP client
- `structlog` - Structured logging

Interactive clients also use:

- `webbrowser` - Browser integration
- `http.server` - Callback server

## Summary

**For user-facing applications:**

- Use **public-client-with-creds** for most cases
- Use **confidential-client** if running on secure backend
- Use **public-client-no-creds** for prototyping/testing

**For automation/background tasks:**

- Use **service-principal** exclusively

**Security ranking (highest to lowest):**

1. Service Principal (app-only, client auth, no browser)
2. Confidential Client (PKCE + client auth)
3. Public Clients (PKCE only)

**Ease of use (easiest to hardest):**

1. Service Principal (no UI, direct token)
2. Public Client (With Creds) (standard OAuth)
3. Confidential Client (OAuth + secret management)
4. Public Client (No Creds) (DCR + OAuth)
