# MCP with Proper Enterprise Authentication

A demonstration of proper enterprise authentication for Model Context Protocol (MCP) servers using Microsoft Entra ID (Azure AD) with OAuth 2.0 and OpenID Connect.

## 🎯 Key Features

- **No Token Minting**: Delegates authentication to Entra ID (Azure AD)
- **DCR Emulation**: Smart client detection for credential-less clients
- **Comprehensive JWT Validation**: Signature, claims, scopes, roles, and more
- **Multiple OAuth Flows**: Auth Code + PKCE, Client Credentials
- **Multi-Client Support**: VS Code, Claude Desktop, Claude Code, ChatGPT
- **Production Ready**: Docker containerized, ECS Fargate & Agent Core deployment

## 🏗️ Architecture

```
MCP Clients → MCP Server (DCR + JWT Validation) → Entra ID
(VS Code,      (FastAPI + Python)                  (OAuth/OIDC)
 Claude, etc.)
```

See [CLAUDE.md](./CLAUDE.md) for comprehensive documentation and [docs/architecture/](./docs/architecture/) for sequence diagrams.

## 🚀 Quick Start

### Prerequisites

- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager (10-100x faster than pip!)
- **Microsoft Entra ID tenant** (Azure AD)
- **Docker** and **Docker Compose**
- **Python 3.11+** (uv can install this for you)

### 1. Configure Entra ID

Create the following app registrations in Entra ID:

1. **MCP Server Resource** (`api://mcp-server`)
   - Expose API scopes: `mcp.read`, `mcp.write`
   - Create app roles: `MCP.Read.All`, `MCP.ReadWrite.All`

2. **Client Applications** (at least one for testing):
   - VS Code MCP Client (public client)
   - Claude Desktop MCP Client (public client)
   - Generic MCP Client (public client, fallback)
   - Optional: Service Principal (for Client Credentials flow)

See [docs/setup/entra-id-setup.md](./docs/setup/entra-id-setup.md) for detailed instructions.

### 2. Install uv (Fast Python Package Manager)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Restart terminal or run: source ~/.bashrc
```

See [UV_SETUP.md](./UV_SETUP.md) for complete guide.

### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Entra ID configuration
# Required values:
#   - ENTRA_TENANT_ID
#   - MCP_SERVER_APP_ID
#   - Client IDs for each client type
```

### 4. Install Dependencies & Run Tests

```bash
cd mcp-server

# Install all dependencies (fast with uv!)
uv sync --extra dev

# Run tests to verify
make test

# Start watch mode for development
make watch
```

### 5. Run with Docker Compose

```bash
# Start MCP server and example clients
docker-compose up -d

# View logs
docker-compose logs -f mcp-server

# Test the health endpoint
curl http://localhost:8000/health
```

### 4. Test the Flows

```bash
# Test DCR emulation
curl -X POST http://localhost:8000/dcr \
  -H "Content-Type: application/json" \
  -H "User-Agent: VSCode-MCP/1.0" \
  -d '{"redirect_uri": "vscode://mcp-auth/callback"}'

# Test with a real client
cd mcp-client-examples/public-client-no-creds
python client.py
```

## 📖 Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Comprehensive project documentation
- **[Architecture Diagrams](./docs/architecture/)** - Sequence diagrams for all flows
- **[Setup Guides](./docs/setup/)** - Entra ID, local dev, deployment
- **[API Documentation](./docs/api/)** - MCP server and DCR endpoints

### Sequence Diagrams

- [DCR Emulation Flow](./docs/architecture/01-dcr-emulation-flow.md)
- [Public Client Auth Flow](./docs/architecture/02-public-client-auth-flow.md)
- [Confidential Client Auth Flow](./docs/architecture/03-confidential-client-auth-flow.md)
- [Service Principal Client Credentials Flow](./docs/architecture/04-service-principal-client-credentials-flow.md)
- [JWT Validation Flow](./docs/architecture/05-jwt-validation-flow.md)

## 🔐 Security Highlights

### JWT Validation

Every incoming token is validated for:

✓ **Signature** - Verified against Entra ID JWKS
✓ **Expiration** (`exp`) - Token not expired
✓ **Not Before** (`nbf`) - Token is valid now
✓ **Issued At** (`iat`) - Token not too old
✓ **Audience** (`aud`) - Matches MCP server app ID
✓ **Issuer** (`iss`) - Matches Entra ID tenant
✓ **Tenant** (`tid`) - Matches allowed tenant(s)
✓ **Scope/Role** - User tokens have `scp`, service principals have `roles`

### OAuth Flows

- **Public Clients**: Authorization Code + PKCE (protects against code interception)
- **Confidential Clients**: Authorization Code + PKCE + Client Secret
- **Service Principals**: Client Credentials Grant (machine-to-machine)

### Defense in Depth

- HTTPS enforced (production)
- Rate limiting on DCR endpoints
- No token logging
- Fail-closed validation
- Clock skew tolerance

## 🛠️ Development

### Local Development (with uv - Recommended!)

```bash
cd mcp-server

# Install dependencies (uv automatically manages virtual env)
uv sync --extra dev

# Run the server
make run
# or
uv run python -m uvicorn app.main:app --reload --port 8000

# Run tests in watch mode (auto-rerun on changes)
make watch
```

Why uv?
- ⚡ **10-100x faster** than pip
- 🔒 **Reproducible** with lockfile
- 🎯 **Simpler** - no manual venv activation
- See [UV_SETUP.md](./UV_SETUP.md) for details

### Running Tests

```bash
cd mcp-server
pytest tests/ -v
```

### Code Structure

```
mcp-server/
├── app/
│   ├── auth/           # JWT validation, JWKS caching
│   ├── dcr/            # DCR emulation, client detection
│   ├── mcp/            # MCP protocol implementation
│   ├── config/         # Configuration management
│   └── main.py         # FastAPI application
└── tests/              # Unit and integration tests
```

## 🚢 Deployment

### AWS ECS Fargate

```bash
# Build and push Docker image
docker build -t mcp-server:latest ./mcp-server
docker tag mcp-server:latest <ecr-repo>/mcp-server:latest
docker push <ecr-repo>/mcp-server:latest

# Deploy with Terraform
cd infrastructure/fargate/terraform
terraform init
terraform apply
```

See [docs/setup/fargate-deployment.md](./docs/setup/fargate-deployment.md) for details.

### Agent Core Runtime

```bash
# Build Docker image
docker build -t mcp-server:latest ./mcp-server

# Deploy to Agent Core
# (Instructions specific to your Agent Core setup)
```

See [docs/setup/agentcore-deployment.md](./docs/setup/agentcore-deployment.md) for details.

## 🧪 Example Clients

The project includes example MCP clients demonstrating each flow:

- **`public-client-no-creds/`** - Public client without client_id (uses DCR)
- **`public-client-with-creds/`** - Public client with pre-configured client_id
- **`confidential-client/`** - Confidential client with client_secret
- **`service-principal/`** - Service principal with Client Credentials flow

Each example is self-contained with its own Dockerfile and can be run independently.

## 📊 Monitoring

The MCP server exposes:

- `/health` - Health check endpoint
- `/ready` - Readiness check endpoint
- `/metrics` - Prometheus metrics (optional)

Logs are structured JSON (configurable) and include:

- Request/response details
- JWT validation results
- DCR emulation decisions
- Error details (without sensitive data)

## 🤝 Contributing

This is a demonstration project. Contributions welcome for:

- Additional client examples
- Improved client detection algorithms
- Performance optimizations
- Documentation improvements
- Bug fixes and security enhancements

## 📝 License

MIT License (TBD)

## 🔗 References

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [Microsoft Identity Platform Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Model Context Protocol](https://github.com/anthropics/anthropic-sdk-python)

## 💬 Questions?

For questions about this implementation or OAuth/OIDC specifics, please open an issue.

---

**Note**: This project demonstrates proper OAuth 2.0 / OpenID Connect integration with enterprise IdP. It does NOT mint its own tokens - all authentication is delegated to Entra ID with comprehensive JWT validation.
