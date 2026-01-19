# Entra ID v2.0 Token Format

This document describes the exact v2.0 token format implemented by the mock Entra ID service, matching the official Microsoft Entra ID specification.

## References

- [Access Token Claims Reference](https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference)
- [Optional Claims Reference](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference)
- [Security Tokens Overview](https://learn.microsoft.com/en-us/entra/identity-platform/security-tokens)

## JWT Header (All Tokens)

```json
{
  "typ": "JWT",
  "alg": "RS256",
  "kid": "<key-identifier>"
}
```

| Claim | Type | Description |
|-------|------|-------------|
| `typ` | String | Always `"JWT"` |
| `alg` | String | Signing algorithm (always `"RS256"`) |
| `kid` | String | Key identifier for JWKS lookup |

## User (Delegated) Token Claims

Issued when a user delegates permissions to an application via authorization code flow.

### Required Claims

```json
{
  "aud": "api://mcp-server",
  "iss": "http://mock-idp:8001/v2.0",
  "iat": 1768706656,
  "nbf": 1768706656,
  "exp": 1768710256,
  "sub": "user-object-id",
  "oid": "user-object-id",
  "tid": "12345678-1234-1234-1234-123456789abc",
  "preferred_username": "user@example.com",
  "name": "User Display Name",
  "scp": "api://mcp-server/.default",
  "appid": "client-app-id",
  "azp": "client-app-id",
  "azpacr": "0",
  "ver": "2.0",
  "uti": "unique-token-id"
}
```
​
### Claim Descriptions

| Claim | Type | Required | Description | V2 Specific |
|-------|------|----------|-------------|-------------|
| **Standard OIDC Claims** | | | | |
| `aud` | String | ✅ | Token audience (always API application ID in v2.0) | ✅ |
| `iss` | String | ✅ | Issuer URL (ends with `/v2.0` for v2 tokens) | ✅ |
| `iat` | Integer | ✅ | Issued at (Unix timestamp) | |
| `nbf` | Integer | ✅ | Not before (Unix timestamp) | |
| `exp` | Integer | ✅ | Expiration time (Unix timestamp) | |
| **User Identity Claims** | | | | |
| `sub` | String | ✅ | Subject (immutable user ID per app) | |
| `oid` | String | ✅ | Object ID (immutable user ID across tenant) | |
| `tid` | String | ✅ | Tenant ID | |
| `preferred_username` | String | ✅ | User's email or UPN | ✅ |
| `name` | String | ✅ | User's display name | |
| **Authorization Claims** | | | | |
| `scp` | String | ✅ | Space-separated scopes (delegated permissions) | ✅ |
| **Client Claims** | | | | |
| `appid` | String | ✅ | Client application ID (v1 compat) | |
| `azp` | String | ✅ | Authorized party (client app ID) | ✅ |
| `azpacr` | String | ✅ | Client auth method: `"0"`=public, `"1"`=secret, `"2"`=cert | ✅ |
| **Token Metadata** | | | | |
| `ver` | String | ✅ | Token version (always `"2.0"`) | ✅ |
| `uti` | String | ✅ | Unique token identifier | |

## App-Only (Service Principal) Token Claims

Issued when an application acts on its own behalf via client credentials flow.

### Required Claims

```json
{
  "aud": "api://mcp-server",
  "iss": "http://mock-idp:8001/v2.0",
  "iat": 1768706656,
  "nbf": 1768706656,
  "exp": 1768710256,
  "sub": "service-principal-oid",
  "oid": "service-principal-oid",
  "tid": "12345678-1234-1234-1234-123456789abc",
  "roles": ["MCP.Read.All", "MCP.ReadWrite.All"],
  "appid": "client-app-id",
  "azp": "client-app-id",
  "azpacr": "1",
  "app_displayname": "Service Principal App",
  "idtyp": "app",
  "ver": "2.0",
  "uti": "unique-token-id"
}
```
​
### Claim Descriptions

| Claim | Type | Required | Description | V2 Specific |
|-------|------|----------|-------------|-------------|
| **Standard OIDC Claims** | | | | |
| `aud` | String | ✅ | Token audience (always API application ID in v2.0) | ✅ |
| `iss` | String | ✅ | Issuer URL (ends with `/v2.0` for v2 tokens) | ✅ |
| `iat` | Integer | ✅ | Issued at (Unix timestamp) | |
| `nbf` | Integer | ✅ | Not before (Unix timestamp) | |
| `exp` | Integer | ✅ | Expiration time (Unix timestamp) | |
| **Service Principal Identity Claims** | | | | |
| `sub` | String | ✅ | Subject (service principal object ID) | |
| `oid` | String | ✅ | Object ID (service principal object ID) | |
| `tid` | String | ✅ | Tenant ID | |
| **Authorization Claims** | | | | |
| `roles` | Array | ✅ | Application roles (application permissions) | ✅ |
| **Client Claims** | | | | |
| `appid` | String | ✅ | Client application ID (v1 compat) | |
| `azp` | String | ✅ | Authorized party (client app ID) | ✅ |
| `azpacr` | String | ✅ | Client auth method: `"1"`=secret, `"2"`=cert | ✅ |
| `app_displayname` | String | ✅ | Service principal display name | |
| **Token Type Indicator** | | | | |
| `idtyp` | String | ✅ | **CRITICAL** - Always `"app"` for app-only tokens | ✅ |
| **Token Metadata** | | | | |
| `ver` | String | ✅ | Token version (always `"2.0"`) | ✅ |
| `uti` | String | ✅ | Unique token identifier | |

## Key Differences: V1.0 vs V2.0

| Aspect | V1.0 | V2.0 |
|--------|------|------|
| **Version claim** | `"ver": "1.0"` | `"ver": "2.0"` |
| **Issuer format** | `https://sts.windows.net/{tenant}/` | `https://login.microsoftonline.com/{tenant}/v2.0` |
| **Client ID claim** | `appid` only | `azp` (with `appid` for compat) |
| **Client auth claim** | `appidacr` | `azpacr` |
| **App-only indicator** | ❌ No specific claim | ✅ `"idtyp": "app"` |
| **Audience format** | Can be resource URI | Always client ID |
| **User claims** | `upn`, `unique_name` | `preferred_username` |

## Critical V2.0 Requirements

### 1. App-Only Token Detection

**V2.0 introduces `idtyp: "app"` to explicitly identify app-only tokens.**

```python
# V2.0: Use idtyp claim
if token.get("idtyp") == "app":
    # App-only token - check roles
    check_roles(token.get("roles", []))
else:
    # User token - check scopes
    check_scopes(token.get("scp", ""))
```
​
### 2. Client Authentication Method (`azpacr`)

The `azpacr` claim indicates how the client authenticated:

- `"0"` - Public client (no client secret or certificate)
- `"1"` - Confidential client using client secret
- `"2"` - Confidential client using certificate

**Usage:**
```python
azpacr = token.get("azpacr", "0")
if azpacr == "2":
    # Higher trust - certificate-based authentication
    grant_privileged_access()
```
​
### 3. Issuer Validation

V2.0 tokens **MUST** have issuer ending in `/v2.0`:

```text
# Valid v2.0 issuers
"https://login.microsoftonline.com/{tenant}/v2.0"
"http://mock-idp:8001/v2.0"  # For testing

# Invalid (v1.0)
"https://sts.windows.net/{tenant}/"
```
​
### 4. Audience Claim

In v2.0, `aud` is **always** the application ID (not resource URI):

```text
# V2.0: Always client ID format
"aud": "api://mcp-server"
"aud": "77777777-7777-7777-7777-777777777777"

# V1.0: Could be resource URI
"aud": "https://management.azure.com/"
```
​
## Optional Claims (Not Included by Default)

These claims require explicit configuration via [optional claims](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference):

| Claim | Description |
|-------|-------------|
| `acr` | Authentication context class |
| `amr` | Authentication methods (pwd, mfa, etc.) |
| `family_name` | User's last name |
| `given_name` | User's first name |
| `ipaddr` | Client IP address |
| `onprem_sid` | On-premises SID |
| `pwd_exp` | Password expiration time |
| `pwd_url` | Password reset URL |
| `groups` | User's group memberships |
| `wids` | Well-known directory role IDs |

## Token Validation Best Practices

### Required Validations

1. **Signature** - Verify using JWKS public key
2. **Issuer** - Must end with `/v2.0`
3. **Audience** - Must match your application ID
4. **Expiration** - `exp` must be in the future
5. **Not Before** - `nbf` must be in the past
6. **Version** - `ver` must be `"2.0"`

### Authorization Validations

#### User (Delegated) Tokens
```python
# Check for delegated permissions
scopes = token.get("scp", "").split()
if "api://mcp-server/.default" not in scopes:
    raise Unauthorized("Missing required scope")
```
​
#### App-Only Tokens
```python
# CRITICAL: Check idtyp first
if token.get("idtyp") != "app":
    raise Unauthorized("Not an app-only token")

# Check for application permissions
roles = token.get("roles", [])
if "MCP.ReadWrite.All" not in roles:
    raise Unauthorized("Missing required role")
```
​
### Security Notes

- ⚠️ **Never use mutable claims** (`name`, `preferred_username`) for authorization
- ✅ **Use `oid`** as the immutable user identifier
- ✅ **Use `idtyp`** to distinguish app vs user tokens
- ✅ **Validate `azpacr`** for trust level decisions
- ⚠️ **Don't assume claim order or presence** - always check with `.get()`

## Example Token Validation

```python
from jose import jwt
from typing import Dict, Any

def validate_v2_token(token: str, jwks_url: str, expected_audience: str) -> Dict[str, Any]:
    """Validate Entra ID v2.0 access token."""

    # Decode header to get kid
    header = jwt.get_unverified_header(token)

    # Fetch JWKS and get key
    jwks = fetch_jwks(jwks_url)
    key = find_key_by_kid(jwks, header["kid"])

    # Decode and validate
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=expected_audience,
        options={
            "verify_signature": True,
            "verify_aud": True,
            "verify_exp": True,
        }
    )

    # V2.0 specific validations
    assert claims["ver"] == "2.0", "Not a v2.0 token"
    assert claims["iss"].endswith("/v2.0"), "Invalid v2.0 issuer"

    # Check token type
    if claims.get("idtyp") == "app":
        # App-only token
        assert "roles" in claims, "Missing roles claim"
        return {"type": "app", "claims": claims}
    else:
        # User token
        assert "scp" in claims, "Missing scp claim"
        return {"type": "user", "claims": claims}
```
​
## Testing with Mock IdP

The mock Entra ID service issues tokens that exactly match this v2.0 specification:

```bash
# Get app-only token
curl -X POST "http://localhost:8001/oauth2/v2.0/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=77777777-7777-7777-7777-777777777777" \
  -d "client_secret=test-sp-secret-456" \
  -d "scope=api://mcp-server/.default"

# Decode token to verify v2.0 format
# Check: ver=2.0, idtyp=app, roles claim present, azpacr=1
```

## Summary

The mock Entra ID implementation provides **100% compliant v2.0 tokens** with:

✅ All required v2.0 claims
✅ Correct header format (`typ`, `alg`, `kid`)
✅ `idtyp: "app"` for app-only tokens
✅ `azpacr` for client authentication method
✅ `ver: "2.0"` version indicator
✅ Issuer ending in `/v2.0`
✅ Both `azp` and `appid` for compatibility
✅ `scp` for user tokens, `roles` for app tokens
❌ No v1.0 legacy claims (unless explicitly requested)
