# Public Client Authentication Flow (Auth Code + PKCE)

This flow is used for public clients
(both those that obtained client_id via DCR and those that already have one).

> **Optional Discovery Step**: Before initiating this flow,
> clients can optionally discover the authorization server and required scopes
> via Protected Resource Metadata.
> See [06-protected-resource-metadata.md](./06-protected-resource-metadata.md).

```mermaid
sequenceDiagram
    participant User
    participant MCP Client (Public)
    participant MCP Server
    participant Entra ID

    Note over MCP Client (Public): Client has client_id<br/>(from DCR or pre-configured)

    User->>MCP Client (Public): Access MCP functionality

    MCP Client (Public)->>MCP Client (Public): Generate PKCE code_verifier
    MCP Client (Public)->>MCP Client (Public): Generate code_challenge
    Note right of MCP Client (Public): code_challenge = <br/>BASE64URL(SHA256(code_verifier))

    MCP Client (Public)->>Entra ID: Authorization Request
    Note right of MCP Client (Public): /authorize?<br/>client_id=...<br/>redirect_uri=...<br/>scope=api://mcp-server/.default<br/>code_challenge=...<br/>code_challenge_method=S256<br/>response_type=code

    Entra ID->>User: Present login page
    User->>Entra ID: Enter credentials + consent

    Entra ID->>Entra ID: User authenticates
    Entra ID->>Entra ID: Generate authorization code

    Entra ID-->>MCP Client (Public): Redirect with auth code
    Note left of Entra ID: redirect_uri?code=...

    MCP Client (Public)->>Entra ID: Token Request
    Note right of MCP Client (Public): POST /token<br/>grant_type=authorization_code<br/>client_id=...<br/>code=...<br/>code_verifier=...<br/>redirect_uri=...

    Entra ID->>Entra ID: Validate code_verifier
    Note right of Entra ID: Verify SHA256(code_verifier)<br/>matches code_challenge

    Entra ID-->>MCP Client (Public): Access Token + ID Token
    Note left of Entra ID: {<br/>  "access_token": "eyJ...",<br/>  "id_token": "eyJ...",<br/>  "token_type": "Bearer",<br/>  "expires_in": 3600<br/>}

    MCP Client (Public)->>MCP Server: MCP Request with token
    Note right of MCP Client (Public): Authorization: Bearer eyJ...

    MCP Server->>MCP Server: Validate JWT
    Note right of MCP Server: - Verify signature (JWKS)<br/>- Check exp, nbf, iat<br/>- Validate aud claim<br/>- Validate iss claim<br/>- Check scp claim for user tokens<br/>- Validate token not revoked

    alt Token valid for user
        MCP Server->>MCP Server: Extract user identity
        Note right of MCP Server: From oid, sub, preferred_username

        MCP Server->>MCP Server: Process MCP request
        MCP Server-->>MCP Client (Public): MCP Response
    else Token invalid
        MCP Server-->>MCP Client (Public): 401 Unauthorized
        Note left of MCP Server: {<br/>  "error": "invalid_token",<br/>  "error_description": "..."<br/>}
    end
```

## Key Points

1. **PKCE (Proof Key for Code Exchange)**:
   - Protects against authorization code interception attacks
   - Required for public clients (per OAuth 2.1)
   - Code verifier: 43-128 character random string
   - Code challenge: Base64URL(SHA256(code_verifier))

2. **Scope**:
   - `api://mcp-server/.default` requests default scopes for the MCP server resource
   - Can be customized to specific scopes like `api://mcp-server/mcp.read`, `api://mcp-server/mcp.write`

3. **JWT Validation** (detailed in separate diagram):
   - Signature validation using JWKS from Entra ID
   - Temporal validation (exp, nbf, iat)
   - Audience validation (aud must match MCP server app ID)
   - Issuer validation (iss must match Entra ID tenant)
   - Scope validation (scp claim for user tokens)
   - Optional: Check for token revocation

4. **User Identity**:
   - `oid` - Object ID (unique identifier)
   - `sub` - Subject (stable identifier)
   - `preferred_username` - User's email/UPN
   - `name` - Display name
