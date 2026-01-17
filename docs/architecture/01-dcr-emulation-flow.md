# DCR Emulation Flow

Since Entra ID doesn't support native Dynamic Client Registration (DCR), the MCP server emulates this by detecting the client type and returning pre-registered client credentials.

```mermaid
sequenceDiagram
    participant MCP Client (Unknown)
    participant MCP Server
    participant Entra ID

    Note over MCP Client (Unknown): Client has no credentials

    MCP Client (Unknown)->>MCP Server: POST /dcr (Dynamic Client Registration)
    Note right of MCP Client (Unknown): Includes redirect_uri,<br/>User-Agent, etc.

    MCP Server->>MCP Server: Analyze client context
    Note right of MCP Server: - Parse redirect_uri<br/>- Check User-Agent<br/>- Match to known client type

    alt Client is VS Code
        MCP Server->>MCP Server: Select VS Code app registration
        Note right of MCP Server: client_id: "vscode-mcp-client"
    else Client is Claude Desktop
        MCP Server->>MCP Server: Select Claude Desktop app registration
        Note right of MCP Server: client_id: "claude-desktop-mcp-client"
    else Client is Claude Code
        MCP Server->>MCP Server: Select Claude Code app registration
        Note right of MCP Server: client_id: "claude-code-mcp-client"
    else Client is ChatGPT
        MCP Server->>MCP Server: Select ChatGPT app registration
        Note right of MCP Server: client_id: "chatgpt-mcp-client"
    else Unknown client
        MCP Server->>MCP Server: Select generic app registration
        Note right of MCP Server: client_id: "generic-mcp-client"
    end

    MCP Server-->>MCP Client (Unknown): Return client credentials
    Note left of MCP Server: {<br/>  "client_id": "...",<br/>  "token_endpoint": "...",<br/>  "authorization_endpoint": "..."<br/>}

    Note over MCP Client (Unknown): Client now has credentials<br/>Proceeds to Auth Code + PKCE flow
```

## Key Points

1. **Client Detection Logic**:
   - `redirect_uri` patterns (e.g., `vscode://`, `claude://`, custom URIs)
   - User-Agent strings
   - Custom headers or metadata in DCR request

2. **Pre-registered App Registrations in Entra ID**:
   - `vscode-mcp-client` - VS Code MCP client
   - `claude-desktop-mcp-client` - Claude Desktop
   - `claude-code-mcp-client` - Claude Code CLI
   - `chatgpt-mcp-client` - ChatGPT integration
   - `generic-mcp-client` - Fallback for unknown clients
   - `mcp-server-resource` - The MCP server as a protected resource

3. **Security Considerations**:
   - DCR endpoint should be rate-limited
   - Client detection should be robust against spoofing
   - Each app registration has specific redirect_uri whitelist in Entra ID
   - MCP server validates that returned client_id matches the detected client type
