# MCP with Proper Enterprise Authentication

## Project Overview

This project demonstrates proper enterprise authentication for Model Context Protocol (MCP) servers using Microsoft Entra ID (Azure AD) with OAuth 2.0 and OpenID Connect. Unlike many examples that "mint their own tokens," this implementation properly delegates authentication to an enterprise Identity Provider (IdP) and performs comprehensive JWT validation.

## Key Features

- **DCR Emulation**: Since Entra ID doesn't support native Dynamic Client Registration, the MCP server intelligently detects client types and returns appropriate pre-registered credentials
- **Multiple OAuth Flows**: Supports Authorization Code + PKCE for user contexts and Client Credentials for service principals
- **Comprehensive JWT Validation**: Validates signature, exp, nbf, iat, aud, iss, tid, scope/roles, and more
- **Multi-Client Support**: Pre-configured for VS Code, Claude Desktop, Claude Code, ChatGPT, and generic clients
- **Dual Deployment**: Runs in AWS ECS Fargate or Agent Core runtime with same codebase
- **Security Best Practices**: Follows OAuth 2.1, OIDC, and JWT best practices throughout

## Architecture

### High-Level Components

```
┌─────────────────┐
│   MCP Clients   │
│                 │
│ - VS Code       │
│ - Claude Desktop│
│ - Claude Code   │
│ - ChatGPT       │
│ - Generic       │
└────────┬────────┘
         │
         │ OAuth 2.0 + JWT
         │
┌────────▼────────┐
│   MCP Server    │
│                 │
│ - DCR Emulation │
│ - JWT Validation│
│ - MCP Protocol  │
└────────┬────────┘
         │
         │ OAuth 2.0
         │
┌────────▼────────┐
│   Entra ID      │
│                 │
│ - Authentication│
│ - Authorization │
│ - Token Issuance│
└─────────────────┘
```

### Supported Authentication Flows

1. **Public Client without Credentials** → DCR Emulation → Auth Code + PKCE
2. **Public Client with client_id** → Auth Code + PKCE
3. **Confidential Client** → Auth Code + PKCE + Client Secret
4. **Service Principal** → Client Credentials Grant

See detailed sequence diagrams in `/docs/architecture/`.

## Token Validation Strategy

The MCP server performs comprehensive JWT validation on every request:

### Signature Verification
- Fetches JWKS from Entra ID (cached for 24 hours)
- Matches signing key by `kid` header
- Verifies RS256 signature with public key

### Temporal Validation
- `exp` (expiration time) must be in the future
- `nbf` (not before time) must be in the past
- `iat` (issued at time) must be reasonable
- 5-minute clock skew tolerance

### Claim Validation
- `iss` (issuer) must match Entra ID endpoint
- `aud` (audience) must match MCP server app ID
- `tid` (tenant ID) must match allowed tenant(s)
- `ver` (token version) should be "2.0"

### Permission Validation
**User Tokens (delegated permissions):**
- Must have `scp` claim with required scopes
- Example: `"mcp.read mcp.write"`

**Service Principal Tokens (application permissions):**
- Must have `roles` claim with required roles
- Example: `["MCP.ReadWrite.All"]`
- `idtyp` claim should be "app"

### Identity Extraction
**User Tokens:**
- `oid` - Object ID (unique user identifier)
- `sub` - Subject (stable identifier)
- `preferred_username` - User's email/UPN
- `name` - Display name

**Service Principal Tokens:**
- `appid` - Application/Client ID
- `oid` - Service principal object ID
- `sub` - Subject (equals oid for app-only)

## Entra ID Configuration

### Required App Registrations

1. **MCP Server Resource** (`mcp-server-resource`)
   - Represents the MCP server as a protected resource
   - App ID URI: `api://mcp-server`
   - Exposed API scopes:
     - `mcp.read` - Read MCP resources
     - `mcp.write` - Write MCP resources
     - `.default` - Default scope
   - App Roles (for service principals):
     - `MCP.Read.All` - Read-only access
     - `MCP.ReadWrite.All` - Full access

2. **VS Code MCP Client** (`vscode-mcp-client`)
   - Public client
   - Redirect URI: `vscode://mcp-auth/callback`
   - API permissions: `api://mcp-server/.default`

3. **Claude Desktop MCP Client** (`claude-desktop-mcp-client`)
   - Public client
   - Redirect URI: `claude://mcp-auth/callback`
   - API permissions: `api://mcp-server/.default`

4. **Claude Code MCP Client** (`claude-code-mcp-client`)
   - Public client
   - Redirect URI: `http://localhost:*/callback` (wildcard port)
   - API permissions: `api://mcp-server/.default`

5. **ChatGPT MCP Client** (`chatgpt-mcp-client`)
   - Public client
   - Redirect URI: (ChatGPT-specific, TBD)
   - API permissions: `api://mcp-server/.default`

6. **Generic MCP Client** (`generic-mcp-client`)
   - Public client (fallback)
   - Redirect URI: `http://localhost:*/callback`
   - API permissions: `api://mcp-server/.default`

7. **Example Confidential Client** (`confidential-mcp-client`)
   - Confidential client
   - Has client secret
   - API permissions: `api://mcp-server/.default`

8. **Example Service Principal** (`service-mcp-client`)
   - Service principal / App registration
   - Has client secret or certificate
   - Assigned app role: `MCP.ReadWrite.All`

### Configuration in Entra ID Portal

1. **Create App Registrations** for each client above
2. **Configure Redirect URIs** with exact matches
3. **Grant API Permissions** (admin consent required for app roles)
4. **Assign App Roles** for service principals via Enterprise Applications
5. **Note down**:
   - Tenant ID
   - Each app's Client ID
   - Client secrets (for confidential clients and service principals)

## Environment Variables

### MCP Server Configuration

```bash
# Entra ID Configuration
ENTRA_TENANT_ID=12345678-1234-1234-1234-123456789abc
ENTRA_AUTHORITY=https://login.microsoftonline.com/${ENTRA_TENANT_ID}

# MCP Server Identity (as a resource)
MCP_SERVER_APP_ID=api://mcp-server
MCP_SERVER_SCOPE_PREFIX=api://mcp-server

# Required scope for user tokens
REQUIRED_SCOPE=mcp.read mcp.write

# Required role for service principal tokens
REQUIRED_ROLE=MCP.ReadWrite.All

# Pre-registered Client IDs (from Entra ID)
VSCODE_CLIENT_ID=11111111-1111-1111-1111-111111111111
CLAUDE_DESKTOP_CLIENT_ID=22222222-2222-2222-2222-222222222222
CLAUDE_CODE_CLIENT_ID=33333333-3333-3333-3333-333333333333
CHATGPT_CLIENT_ID=44444444-4444-4444-4444-444444444444
GENERIC_CLIENT_ID=55555555-5555-5555-5555-555555555555

# Deployment Configuration
DEPLOYMENT_MODE=fargate  # or "agentcore"
MCP_SERVER_PORT=8000
MCP_SERVER_HOST=0.0.0.0

# Optional: Token Revocation
ENABLE_TOKEN_REVOCATION=false
REDIS_URL=redis://localhost:6379  # If revocation enabled

# Optional: Logging
LOG_LEVEL=INFO
```

### MCP Client Configuration (Example)

```bash
# Client Identity (obtained via DCR or pre-configured)
CLIENT_ID=11111111-1111-1111-1111-111111111111
CLIENT_SECRET=  # Empty for public clients

# MCP Server Endpoint
MCP_SERVER_URL=https://mcp-server.example.com

# Entra ID Configuration
ENTRA_TENANT_ID=12345678-1234-1234-1234-123456789abc
ENTRA_AUTHORITY=https://login.microsoftonline.com/${ENTRA_TENANT_ID}

# OAuth Configuration
SCOPE=api://mcp-server/.default
REDIRECT_URI=vscode://mcp-auth/callback
```

## Technology Stack

### MCP Server
- **Python 3.11+**
- **FastAPI** - Web framework
- **python-jose[cryptography]** - JWT validation
- **cryptography** - Cryptographic operations
- **httpx** - Async HTTP client
- **pydantic** - Data validation
- **uvicorn** - ASGI server
- **redis** (optional) - Token revocation cache

### MCP Client (Example)
- **Python 3.11+**
- **mcp** - MCP SDK
- **httpx** - HTTP client
- **authlib** - OAuth client

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local orchestration
- **AWS ECS Fargate** - Production deployment
- **Agent Core** - Alternative runtime

## Project Structure

```
mcp-with-proper-enterprise-auth/
├── CLAUDE.md                          # This file
├── README.md                          # Quick start guide
├── docker-compose.yml                 # Local development setup
│
├── docs/
│   ├── architecture/                  # Architecture diagrams
│   │   ├── 01-dcr-emulation-flow.md
│   │   ├── 02-public-client-auth-flow.md
│   │   ├── 03-confidential-client-auth-flow.md
│   │   ├── 04-service-principal-client-credentials-flow.md
│   │   └── 05-jwt-validation-flow.md
│   │
│   ├── setup/                         # Setup guides
│   │   ├── entra-id-setup.md         # Entra ID configuration
│   │   ├── local-development.md      # Local dev setup
│   │   ├── fargate-deployment.md     # AWS ECS deployment
│   │   └── agentcore-deployment.md   # Agent Core deployment
│   │
│   └── api/                           # API documentation
│       ├── mcp-server-api.md         # MCP server endpoints
│       └── dcr-endpoints.md          # DCR emulation API
│
├── mcp-server/                        # MCP Server implementation
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   │
│   │   ├── auth/                     # Authentication module
│   │   │   ├── __init__.py
│   │   │   ├── jwt_validator.py     # JWT validation logic
│   │   │   ├── jwks_cache.py        # JWKS caching
│   │   │   ├── token_validator.py   # Token type detection
│   │   │   └── middleware.py        # Auth middleware
│   │   │
│   │   ├── dcr/                      # DCR emulation module
│   │   │   ├── __init__.py
│   │   │   ├── client_detector.py   # Detect client type
│   │   │   ├── client_registry.py   # Client config
│   │   │   └── endpoints.py         # DCR endpoints
│   │   │
│   │   ├── mcp/                      # MCP protocol module
│   │   │   ├── __init__.py
│   │   │   ├── server.py            # MCP server implementation
│   │   │   ├── tools.py             # MCP tools
│   │   │   └── resources.py         # MCP resources
│   │   │
│   │   ├── config/                   # Configuration
│   │   │   ├── __init__.py
│   │   │   └── settings.py          # Pydantic settings
│   │   │
│   │   └── utils/                    # Utilities
│   │       ├── __init__.py
│   │       ├── logging.py           # Logging setup
│   │       └── exceptions.py        # Custom exceptions
│   │
│   └── tests/                         # Tests
│       ├── __init__.py
│       ├── test_jwt_validation.py
│       ├── test_dcr.py
│       └── test_mcp.py
│
├── mcp-client-examples/               # Example MCP clients
│   │
│   ├── public-client-no-creds/       # Public client without client_id
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── client.py
│   │
│   ├── public-client-with-creds/     # Public client with client_id
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── client.py
│   │
│   ├── confidential-client/          # Confidential client
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── client.py
│   │
│   └── service-principal/            # Service principal client
│       ├── Dockerfile
│       ├── requirements.txt
│       └── client.py
│
├── infrastructure/                    # Infrastructure as Code
│   ├── fargate/                      # AWS ECS Fargate
│   │   ├── terraform/                # Terraform configs
│   │   └── cloudformation/           # CloudFormation templates
│   │
│   └── agentcore/                    # Agent Core configs
│       └── deployment.yaml
│
└── scripts/                           # Utility scripts
    ├── setup-entra-id.sh             # Automate Entra ID setup
    ├── generate-env.sh               # Generate .env files
    └── test-flows.sh                 # Test all OAuth flows
```

## Getting Started

### Prerequisites

1. **Microsoft Entra ID Tenant** (Azure AD)
2. **Docker** and **Docker Compose**
3. **Python 3.11+** (for local development)
4. **AWS Account** (for Fargate deployment)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd mcp-with-proper-enterprise-auth
   ```

2. **Configure Entra ID**
   - Follow `docs/setup/entra-id-setup.md` to create app registrations
   - Note down tenant ID, client IDs, and secrets

3. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your Entra ID configuration
   ```

4. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

5. **Test the flows**
   ```bash
   ./scripts/test-flows.sh
   ```

## Development Roadmap

### Phase 1: Core Implementation ✓
- [x] Architecture design and sequence diagrams
- [x] JWT validation strategy
- [x] Project structure
- [ ] MCP server implementation
- [ ] DCR emulation logic
- [ ] Example MCP clients

### Phase 2: Testing & Documentation
- [ ] Comprehensive unit tests
- [ ] Integration tests for all flows
- [ ] API documentation
- [ ] Setup guides for Entra ID

### Phase 3: Deployment
- [ ] Docker containerization
- [ ] Docker Compose orchestration
- [ ] AWS ECS Fargate deployment guide
- [ ] Agent Core deployment guide

### Phase 4: Advanced Features
- [ ] CloudFront/AgentCore proxy simulation
- [ ] Monitoring and logging

## Security Considerations

### Token Security
- Tokens are never logged
- Tokens are validated on every request
- Short-lived tokens (1 hour default)
- HTTPS required for all endpoints (enforced in production)

### Client Secret Management
- Secrets stored in environment variables
- Never committed to version control
- Rotated regularly (manual process initially)
- Consider Azure Key Vault for production

### PKCE (Proof Key for Code Exchange)
- Required for all public clients
- Recommended for confidential clients (defense in depth)
- SHA-256 code challenge method

### JWT Validation
- Signature verification with JWKS
- All temporal claims validated (exp, nbf, iat)
- Audience and issuer strictly validated
- Proper scope/role validation based on token type

### Defense in Depth
- Multiple layers of validation
- Fail closed (deny by default)
- Detailed error logging (without exposing sensitive data)
- Rate limiting on DCR endpoints

## Known Limitations & Future Work

1. **DCR Emulation**: Not true DCR - pre-registration required in Entra ID
2. **Token Revocation**: Optional feature, requires Redis
3. **ChatGPT Integration**: May require special handling (TBD)
4. **Multi-Tenancy**: Currently single-tenant, can be extended
5. **Certificate-Based Auth**: Not yet implemented for service principals
6. **Agent Core**: Full simulation deferred to Phase 4

## References

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-07)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Model Context Protocol](https://github.com/anthropics/anthropic-sdk-python/tree/main/src/anthropic/lib/mcp)

## Contributing

This is a demonstration project. Contributions welcome for:
- Additional client examples
- Improved client detection logic
- Performance optimizations
- Documentation improvements
- Bug fixes

## License

MIT License (TBD)

## Contact

For questions about this implementation approach or OAuth/OIDC specifics, please open an issue.
