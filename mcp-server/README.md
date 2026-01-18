# MCP Server Implementation

This directory contains the MCP (Model Context Protocol) server implementation with proper enterprise authentication via Microsoft Entra ID (Azure AD).

## Architecture

The server is built with:
- **FastAPI**: Modern, fast web framework
- **python-jose**: JWT validation with cryptography
- **Pydantic**: Configuration management and validation
- **Structlog**: Structured logging

## Directory Structure

```text
app/
├── __init__.py
├── main.py                    # FastAPI application entry point
│
├── auth/                      # Authentication module
│   ├── __init__.py
│   ├── jwks_cache.py         # JWKS caching with TTL
│   ├── jwt_validator.py      # Comprehensive JWT validation
│   ├── token_validator.py    # Token type detection & permission validation
│   └── middleware.py         # Authentication middleware & dependencies
│
├── dcr/                       # DCR emulation module
│   ├── __init__.py
│   ├── client_detector.py    # Client type detection (VS Code, Claude, etc.)
│   ├── client_registry.py    # Client credentials registry
│   └── endpoints.py          # DCR API endpoints
│
├── mcp/                       # MCP protocol module
│   └── __init__.py           # (Placeholder for MCP protocol implementation)
│
├── config/                    # Configuration module
│   ├── __init__.py
│   └── settings.py           # Pydantic settings with env var loading
│
└── utils/                     # Utilities
    ├── __init__.py
    ├── exceptions.py         # Custom exception classes
    └── logging.py            # Logging configuration
```

## Key Components

### Authentication Flow

1. **JWT Extraction**: Extract Bearer token from Authorization header
2. **JWKS Retrieval**: Fetch/cache public keys from Entra ID
3. **Signature Verification**: Verify RS256 signature with JWKS
4. **Claims Validation**: Validate exp, nbf, iat, aud, iss, tid
5. **Token Type Detection**: Detect user token (scp) vs app-only (roles)
6. **Permission Validation**: Validate required scopes or roles
7. **Identity Extraction**: Extract user or service principal identity
8. **Auth Context**: Attach validated auth context to request

### DCR Emulation

Since Entra ID doesn't support native DCR, the server emulates it:

1. **Client Detection**: Analyze redirect_uri, User-Agent, client_name
2. **Type Mapping**: Map to known client types (VS Code, Claude, etc.)
3. **Credentials Return**: Return pre-registered client_id from Entra ID
4. **OAuth Endpoints**: Return Entra ID OAuth endpoints

Detection priority:
1. Redirect URI (most reliable)
2. User-Agent
3. Client name
4. Fallback to generic client

### JWT Validation Layers

1. ✓ Structure & format (3-part JWT)
2. ✓ Signature verification (RS256 with JWKS)
3. ✓ Temporal validation (exp, nbf, iat with clock skew)
4. ✓ Required claims (iss, aud, exp, iat, sub, tid)
5. ✓ Issuer validation (matches Entra ID)
6. ✓ Audience validation (matches MCP server app ID)
7. ✓ Tenant validation (matches allowed tenant)
8. ✓ Token version validation (AAD v2.0)

### Permission Validation

**User Tokens (Delegated Permissions):**
- Must have `scp` claim
- Validates required scope(s)
- Supports AND/OR logic for scopes

**App-Only Tokens (Application Permissions):**
- Must have `roles` claim
- Validates required role(s)
- Typically uses OR logic (any role)

## Running the Server

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (or use .env file)
export ENTRA_TENANT_ID="your-tenant-id"
export MCP_SERVER_APP_ID="api://mcp-server"
# ... (see .env.example for all variables)

# Run server
python -m uvicorn app.main:app --reload --port 8000

# Or use the main script
python app/main.py
```

### With Docker

```bash
# Build image
docker build -t mcp-server:latest .

# Run container
docker run -p 8000:8000 --env-file .env mcp-server:latest
```

### With Docker Compose (from project root)

```bash
# Start server
docker-compose up -d mcp-server

# View logs
docker-compose logs -f mcp-server

# Stop server
docker-compose down
```

## API Endpoints

### Public Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /docs` - Swagger UI (if enabled)
- `POST /dcr/register` - DCR emulation (if enabled)

### Protected Endpoints (require authentication)

- `GET /api/me` - Get current user/app information

All protected endpoints require:
- `Authorization: Bearer <jwt_token>` header
- Valid JWT from Entra ID
- Required scopes (for user tokens) or roles (for app-only tokens)

## Testing

### Unit Tests

```bash
pytest tests/ -v
```

### Test with Mock Authentication

For testing without Entra ID:

```bash
# Set ENABLE_MOCK_AUTH=true in .env
export ENABLE_MOCK_AUTH=true

# Start server
python app/main.py

# Call protected endpoint without token
curl http://localhost:8000/api/me
```

**WARNING**: Never enable mock auth in production!

### Test DCR Emulation

```bash
# VS Code client
curl -X POST http://localhost:8000/dcr/register \
  -H "Content-Type: application/json" \
  -H "User-Agent: VSCode-MCP/1.0" \
  -d '{
    "redirect_uris": ["vscode://mcp-auth/callback"]
  }'

# Claude Code client
curl -X POST http://localhost:8000/dcr/register \
  -H "Content-Type: application/json" \
  -H "User-Agent: Claude-CLI/1.0" \
  -d '{
    "redirect_uris": ["http://localhost:8080/callback"],
    "client_name": "Claude Code"
  }'
```

### Test JWT Validation

```bash
# Get a real token from Entra ID (using OAuth flow)
TOKEN="your-jwt-token-here"

# Call protected endpoint
curl http://localhost:8000/api/me \
  -H "Authorization: Bearer $TOKEN"
```

## Configuration

All configuration is managed via environment variables using Pydantic Settings.

Required variables:
- `ENTRA_TENANT_ID`
- `MCP_SERVER_APP_ID`
- `REQUIRED_SCOPE`
- `REQUIRED_ROLE`
- Client IDs (VSCODE_CLIENT_ID, CLAUDE_DESKTOP_CLIENT_ID, etc.)

See `../.env.example` for complete list.

## Logging

The server uses structured logging with configurable format:

**JSON format (production):**
```json
{"timestamp": "2026-01-17T...", "level": "INFO", "message": "jwt_validated", "sub": "user-id"}
```

**Text format (development):**
```text
2026-01-17 12:34:56 - app.auth.jwt_validator - INFO - jwt_validated sub=user-id
```

Configure via:
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `LOG_FORMAT`: json, text
- `LOG_REQUESTS`: true/false
- `LOG_JWT_CLAIMS`: true/false (NEVER enable in production!)

## Security Considerations

1. **No token minting**: All tokens issued by Entra ID
2. **Comprehensive validation**: 8-layer JWT validation
3. **JWKS caching**: 24-hour TTL, auto-refresh on kid mismatch
4. **Clock skew tolerance**: 5 minutes (configurable)
5. **Rate limiting**: DCR endpoint rate-limited per IP
6. **Non-root user**: Docker container runs as non-root
7. **No sensitive logging**: Tokens never logged (unless DEBUG + LOG_JWT_CLAIMS)
8. **CORS**: Configurable allowed origins

## Performance

- **JWKS caching**: Reduces latency and Entra ID API calls
- **Async I/O**: All I/O operations are async (JWKS fetch, etc.)
- **Multiple workers**: Uvicorn can run with multiple workers
- **Connection pooling**: HTTP client with connection pooling

## Deployment

### AWS ECS Fargate

See `../infrastructure/fargate/` for deployment configurations.

### Agent Core

See `../infrastructure/agentcore/` for deployment configurations.

## Troubleshooting

### Common Issues

**"Missing Authorization header"**
- Ensure `Authorization: Bearer <token>` header is present
- Check if token is being passed correctly

**"Token has expired"**
- Token lifetime is controlled by Entra ID (typically 1 hour)
- Refresh token or re-authenticate

**"Invalid token version"**
- Ensure you're using AAD v2.0 tokens (ver: "2.0")
- Check token endpoint URL includes `/v2.0`

**"JWKS key not found"**
- JWKS cache may be stale
- Server will auto-refresh JWKS once
- Check Entra ID JWKS endpoint is accessible

**"Insufficient permissions"**
- User token: Missing required scope in `scp` claim
- App-only token: Missing required role in `roles` claim
- Verify app registration permissions and admin consent

### Debug Mode

Enable debug mode for detailed error messages:

```bash
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG
export LOG_JWT_CLAIMS=true  # Shows full JWT claims (NEVER in production!)
```

## Next Steps

- Implement full MCP protocol handler in `app/mcp/`
- Add integration tests with real Entra ID tokens
- Add Prometheus metrics endpoint
- Implement token revocation checking (optional, requires Redis)
- Add more comprehensive error handling and retries

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-jose Documentation](https://python-jose.readthedocs.io/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
