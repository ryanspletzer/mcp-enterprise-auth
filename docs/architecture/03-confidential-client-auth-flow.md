# Confidential Client Authentication Flow (Auth Code + PKCE + Client Secret)

This flow is used for confidential clients that have both client_id and client_secret. Still uses Auth Code flow for user context, but authenticates the client itself.

```mermaid
sequenceDiagram
    participant User
    participant MCP Client (Confidential)
    participant MCP Server
    participant Entra ID

    Note over MCP Client (Confidential): Client has client_id + client_secret

    User->>MCP Client (Confidential): Access MCP functionality

    MCP Client (Confidential)->>MCP Client (Confidential): Generate PKCE code_verifier
    MCP Client (Confidential)->>MCP Client (Confidential): Generate code_challenge

    MCP Client (Confidential)->>Entra ID: Authorization Request
    Note right of MCP Client (Confidential): /authorize?<br/>client_id=...<br/>redirect_uri=...<br/>scope=api://mcp-server/.default<br/>code_challenge=...<br/>code_challenge_method=S256<br/>response_type=code

    Entra ID->>User: Present login page
    User->>Entra ID: Enter credentials + consent

    Entra ID->>Entra ID: User authenticates
    Entra ID-->>MCP Client (Confidential): Redirect with auth code

    MCP Client (Confidential)->>Entra ID: Token Request with client authentication
    Note right of MCP Client (Confidential): POST /token<br/>grant_type=authorization_code<br/>client_id=...<br/>client_secret=...<br/>code=...<br/>code_verifier=...<br/>redirect_uri=...

    Entra ID->>Entra ID: Validate client_secret
    Entra ID->>Entra ID: Validate code_verifier
    Note right of Entra ID: Double authentication:<br/>- Client (via secret)<br/>- User (via code)

    Entra ID-->>MCP Client (Confidential): Access Token + ID Token
    Note left of Entra ID: Token contains:<br/>- User identity (oid, sub)<br/>- App identity (appid, azp)<br/>- User scopes (scp)

    MCP Client (Confidential)->>MCP Server: MCP Request with token
    Note right of MCP Client (Confidential): Authorization: Bearer eyJ...

    MCP Server->>MCP Server: Validate JWT
    Note right of MCP Server: - Verify signature<br/>- Check exp, nbf, iat<br/>- Validate aud claim<br/>- Validate iss claim<br/>- Check scp claim (user token)<br/>- Validate appid/azp (client identity)

    alt Token valid
        MCP Server->>MCP Server: Extract identities
        Note right of MCP Server: User: oid, sub, preferred_username<br/>Client: appid, azp

        MCP Server->>MCP Server: Process MCP request
        MCP Server-->>MCP Client (Confidential): MCP Response
    else Token invalid
        MCP Server-->>MCP Client (Confidential): 401 Unauthorized
    end
```

## Key Points

1. **Client Authentication**:
   - Confidential clients authenticate with `client_secret`
   - This is in addition to the authorization code flow
   - Provides stronger assurance of client identity

2. **Still Uses PKCE**:
   - Even confidential clients should use PKCE (defense in depth)
   - Protects against additional attack vectors
   - Recommended by OAuth 2.1 for all client types

3. **Token Contains Both Identities**:
   - **User identity**: `oid`, `sub`, `preferred_username`, `name`
   - **Client identity**: `appid`, `azp` (authorized party)
   - Allows server to track both who the user is and which client is acting

4. **JWT Claims Validation**:
   - `scp` claim indicates this is a delegated permission (user token)
   - `appid`/`azp` shows which client app is being used
   - Can implement client-specific policies based on `appid`

5. **Use Cases**:
   - Server-side web applications
   - Backend services acting on behalf of users
   - Scenarios requiring stronger client authentication
