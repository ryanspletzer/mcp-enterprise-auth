# Mock Entra ID Token Issuer

A standalone mock OAuth 2.0/OIDC token issuer that emulates Microsoft Entra ID (Azure AD)
for testing and demos.

## Features

- **Full OAuth 2.0/OIDC Support**: Authorization Code, Client Credentials, Refresh Token flows
- **PKCE Support**: Full PKCE implementation with SHA256 code challenge/verifier
- **Realistic UI**: Microsoft-styled login and consent pages
- **JWT Token Generation**: RS256-signed tokens with Entra ID-compatible claims
- **JWKS Endpoint**: Serves RSA public keys for token validation
- **Multiple Client Types**: Public, confidential, and service principal flows
- **In-Memory Storage**: Fast, stateless operation (optional Redis backend)

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install with dev dependencies
pip install -r requirements-dev.txt

# Install Playwright browsers (for E2E tests)
playwright install chromium
```

### Running the Server

```bash
# Copy environment configuration
cp .env.example .env

# Edit .env with your configuration
nano .env

# Start the server
uvicorn app.main:app --reload --port 8001

# Or use the convenience script
python -m app.main
```

The mock IdP will be available at `http://localhost:8001`.

### Key Endpoints

- `GET /oauth2/v2.0/authorize` - Authorization endpoint
- `POST /oauth2/v2.0/token` - Token endpoint
- `GET /discovery/v2.0/keys` - JWKS endpoint
- `GET /.well-known/openid-configuration` - OIDC discovery
- `GET /health` - Health check

## Configuration

All configuration is done via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `MOCK_TENANT_ID` | Mock tenant ID for token claims | UUID |
| `MOCK_IDP_PORT` | Port to run the server | 8001 |
| `ACCESS_TOKEN_TTL` | Access token lifetime (seconds) | 3600 |
| `MCP_SERVER_APP_ID` | Audience claim for tokens | api://mcp-server |

## Pre-registered Clients

The mock IdP comes pre-configured with test clients:

| Client ID | Type | Client Secret | Use Case |
|-----------|------|---------------|----------|
| `11111111-1111-1111-1111-111111111111` | Public | None | VS Code Extension |
| `33333333-3333-3333-3333-333333333333` | Public | None | Claude Code CLI |
| `66666666-6666-6666-6666-666666666666` | Confidential | `test-secret-123` | Backend App |
| `77777777-7777-7777-7777-777777777777` | Confidential | `test-sp-secret-456` | Service Principal |

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run E2E tests (requires Playwright)
pytest tests/e2e/ -v
```

## Usage Examples

### Authorization Code Flow (with PKCE)

```bash
# 1. Generate PKCE code_verifier and code_challenge
CODE_VERIFIER=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-43)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | base64 | tr -d '=+/' | tr '/+' '_-')

# 2. Navigate to authorization endpoint (in browser)
open "http://localhost:8001/oauth2/v2.0/authorize?client_id=33333333-3333-3333-3333-333333333333&redirect_uri=http://localhost:8080/callback&response_type=code&scope=api://mcp-server/.default&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256&state=random-state"

# 3. After login and consent, you'll be redirected with an authorization code
# Extract the code from the redirect URL

# 4. Exchange code for token
curl -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=33333333-3333-3333-3333-333333333333" \
  -d "code=<AUTHORIZATION_CODE>" \
  -d "redirect_uri=http://localhost:8080/callback" \
  -d "code_verifier=$CODE_VERIFIER"
```

### Client Credentials Flow

```bash
curl -X POST http://localhost:8001/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=77777777-7777-7777-7777-777777777777" \
  -d "client_secret=test-sp-secret-456" \
  -d "scope=api://mcp-server/.default"
```

### JWKS Retrieval

```bash
curl http://localhost:8001/discovery/v2.0/keys
```

## Integration with MCP Server

To configure the MCP server to use the mock IdP:

```bash
# In mcp-server/.env
ENTRA_TENANT_ID=12345678-1234-1234-1234-123456789abc
ENTRA_AUTHORITY=http://localhost:8001
ENTRA_JWKS_URL=http://localhost:8001/discovery/v2.0/keys
```

## Development

```bash
# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Linting
ruff check app/ tests/
```

## Architecture

```text
mock-entra-idp/
├── app/
│   ├── config/          # Pydantic settings
│   ├── crypto/          # JWT signing and key management
│   ├── endpoints/       # OAuth endpoints (authorize, token, JWKS)
│   ├── models/          # Data models (Client, Token, AuthCode, etc.)
│   ├── storage/         # Storage backends (memory, Redis)
│   ├── templates/       # Jinja2 HTML templates
│   ├── static/          # CSS, JS, images
│   └── utils/           # Helpers (PKCE, validators)
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # Playwright E2E tests
└── scripts/             # Utility scripts
```

## License

MIT
