# Environment Variables Reference

This document provides a comprehensive reference for all environment variables
used in the MCP server and client applications.

## Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENTRA_TENANT_ID` | Yes | - | Your Entra ID tenant ID |
| `MCP_SERVER_APP_ID` | Yes | - | MCP server app ID or URI |
| `REQUIRED_SCOPE` | Yes | - | Required scope for user tokens |
| `REQUIRED_ROLE` | Yes | - | Required role for service principals |
| `VSCODE_CLIENT_ID` | Yes | - | VS Code client app ID |
| `CLAUDE_DESKTOP_CLIENT_ID` | Yes | - | Claude Desktop client app ID |
| `CLAUDE_CODE_CLIENT_ID` | Yes | - | Claude Code client app ID |
| `CHATGPT_CLIENT_ID` | Yes | - | ChatGPT client app ID |
| `GENERIC_CLIENT_ID` | Yes | - | Generic fallback client app ID |

## Detailed Reference

### Entra ID Configuration

#### `ENTRA_TENANT_ID`

- **Type**: UUID
- **Required**: Yes
- **Example**: `12345678-1234-1234-1234-123456789abc`
- **Description**: Your Microsoft Entra ID (Azure AD) tenant ID.
  Found in Azure Portal -> Entra ID -> Overview.

#### `ENTRA_AUTHORITY`

- **Type**: URL
- **Required**: No
- **Default**: `https://login.microsoftonline.com/${ENTRA_TENANT_ID}`
- **Example**: `https://login.microsoftonline.com/12345678-1234-1234-1234-123456789abc`
- **Description**: The OAuth authority URL. Usually auto-constructed from tenant ID.

#### `ENTRA_OIDC_CONFIG_URL`

- **Type**: URL
- **Required**: No
- **Default**: `https://login.microsoftonline.com/${ENTRA_TENANT_ID}/v2.0/.well-known/openid-configuration`
- **Description**: OpenID Connect discovery endpoint. Auto-constructed if not provided.

#### `ENTRA_JWKS_URL`

- **Type**: URL
- **Required**: No
- **Default**: `https://login.microsoftonline.com/${ENTRA_TENANT_ID}/discovery/v2.0/keys`
- **Description**: JSON Web Key Set endpoint for token signature verification.

---

### MCP Server Identity

#### `MCP_SERVER_APP_ID`

- **Type**: String (URI or UUID)
- **Required**: Yes
- **Example**: `api://mcp-server` or `87654321-4321-4321-4321-cba987654321`
- **Description**: The identifier for your MCP server app registration.
  This is the audience (`aud`) claim expected in JWTs.
  Can be the App ID URI or the client ID GUID.

#### `MCP_SERVER_SCOPE_PREFIX`

- **Type**: String (URI)
- **Required**: No
- **Default**: Value of `MCP_SERVER_APP_ID`
- **Example**: `api://mcp-server`
- **Description**: Prefix for scopes. Used when validating scope claims.

---

### Authorization Requirements

#### `REQUIRED_SCOPE`

- **Type**: String (space-separated)
- **Required**: Yes (for user token validation)
- **Example**: `mcp.read mcp.write`
- **Description**: Required scope(s) in the `scp` claim for user (delegated) tokens.
  Token must have at least one of these scopes.

#### `REQUIRED_SCOPES_ANY`

- **Type**: String (comma-separated)
- **Required**: No
- **Example**: `mcp.read,mcp.write`
- **Description**: Alternative to `REQUIRED_SCOPE`.
  Token must have ANY of these scopes (OR logic).

#### `REQUIRED_SCOPES_ALL`

- **Type**: String (comma-separated)
- **Required**: No
- **Example**: `mcp.read,mcp.write`
- **Description**: Alternative to `REQUIRED_SCOPE`.
  Token must have ALL of these scopes (AND logic).

#### `REQUIRED_ROLE`

- **Type**: String
- **Required**: Yes (for service principal validation)
- **Example**: `MCP.ReadWrite.All`
- **Description**: Required role in the `roles` claim for service principal (app-only) tokens.

#### `REQUIRED_ROLES_ANY`

- **Type**: String (comma-separated)
- **Required**: No
- **Example**: `MCP.Read.All,MCP.ReadWrite.All`
- **Description**: Alternative to `REQUIRED_ROLE`.
  Token must have ANY of these roles (OR logic).

---

### Pre-registered Client IDs

These are the client IDs of app registrations created in Entra ID for each MCP client type.

#### `VSCODE_CLIENT_ID`

- **Type**: UUID
- **Required**: Yes
- **Example**: `11111111-1111-1111-1111-111111111111`
- **Description**: Client ID for VS Code MCP client app registration.

#### `CLAUDE_DESKTOP_CLIENT_ID`

- **Type**: UUID
- **Required**: Yes
- **Example**: `22222222-2222-2222-2222-222222222222`
- **Description**: Client ID for Claude Desktop MCP client app registration.

#### `CLAUDE_CODE_CLIENT_ID`

- **Type**: UUID
- **Required**: Yes
- **Example**: `33333333-3333-3333-3333-333333333333`
- **Description**: Client ID for Claude Code CLI MCP client app registration.

#### `CHATGPT_CLIENT_ID`

- **Type**: UUID
- **Required**: Yes
- **Example**: `44444444-4444-4444-4444-444444444444`
- **Description**: Client ID for ChatGPT MCP client app registration.

#### `GENERIC_CLIENT_ID`

- **Type**: UUID
- **Required**: Yes
- **Example**: `55555555-5555-5555-5555-555555555555`
- **Description**: Client ID for generic/fallback MCP client app registration.
  Used when client type cannot be determined.

#### `CONFIDENTIAL_CLIENT_ID` / `CONFIDENTIAL_CLIENT_SECRET`

- **Type**: UUID / String
- **Required**: No (for testing confidential clients)
- **Description**: Client ID and secret for testing confidential client flow.

#### `SERVICE_PRINCIPAL_CLIENT_ID` / `SERVICE_PRINCIPAL_CLIENT_SECRET`

- **Type**: UUID / String
- **Required**: No (for testing service principals)
- **Description**: Client ID and secret for testing service principal (Client Credentials) flow.

---

### MCP Server Configuration

#### `DEPLOYMENT_MODE`

- **Type**: Enum
- **Required**: No
- **Default**: `fargate`
- **Options**: `fargate`, `agentcore`
- **Description**: Deployment mode. Affects certain behaviors and defaults.

#### `MCP_SERVER_HOST`

- **Type**: String
- **Required**: No
- **Default**: `0.0.0.0`
- **Description**: Host address to bind the server to.

#### `MCP_SERVER_PORT`

- **Type**: Integer
- **Required**: No
- **Default**: `8000`
- **Description**: Port number for the server.

#### `MCP_SERVER_BASE_URL`

- **Type**: URL
- **Required**: No
- **Default**: `http://localhost:8000`
- **Example**: `https://mcp-server.example.com`
- **Description**: Public base URL of the MCP server.
  Used for generating callback URLs, etc.

---

### JWT Validation Configuration

#### `JWT_CLOCK_SKEW_SECONDS`

- **Type**: Integer
- **Required**: No
- **Default**: `300` (5 minutes)
- **Description**: Clock skew tolerance in seconds for exp, nbf, and iat validation.

#### `JWKS_CACHE_TTL_SECONDS`

- **Type**: Integer
- **Required**: No
- **Default**: `86400` (24 hours)
- **Description**: Time-to-live for cached JWKS (JSON Web Key Set) in seconds.

#### `VALIDATE_TOKEN_VERSION`

- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Whether to validate the `ver` claim in tokens.
  Should be "2.0" for AAD v2.0 tokens.

#### `ALLOWED_TOKEN_VERSIONS`

- **Type**: String (comma-separated)
- **Required**: No
- **Default**: `2.0`
- **Description**: Allowed token versions. Usually just "2.0" for modern Entra ID tokens.

#### `ENFORCE_HTTPS_REDIRECTS`

- **Type**: Boolean
- **Required**: No
- **Default**: `false` (local dev), `true` (production)
- **Description**: Whether to enforce HTTPS for redirect URIs.
  Disable for local development.

---

### Token Revocation (Optional)

#### `ENABLE_TOKEN_REVOCATION`

- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Description**: Enable token revocation checking via Redis cache.

#### `REDIS_URL`

- **Type**: URL
- **Required**: If `ENABLE_TOKEN_REVOCATION=true`
- **Example**: `redis://localhost:6379/0`
- **Description**: Redis connection string for token revocation cache.

#### `REDIS_PASSWORD`

- **Type**: String
- **Required**: No
- **Description**: Redis password if authentication is required.

#### `REVOCATION_CACHE_TTL_SECONDS`

- **Type**: Integer
- **Required**: No
- **Default**: `3600` (1 hour)
- **Description**: TTL for revocation cache entries.
  Should match or exceed token expiration.

---

### DCR Emulation Configuration

#### `ENABLE_DCR_ENDPOINT`

- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable the DCR (Dynamic Client Registration) emulation endpoint.

#### `DCR_RATE_LIMIT_PER_MINUTE`

- **Type**: Integer
- **Required**: No
- **Default**: `10`
- **Description**: Rate limit for DCR requests per IP address per minute.

---

### Security Configuration

#### `CORS_ALLOWED_ORIGINS`

- **Type**: String (comma-separated URLs)
- **Required**: No
- **Default**: `http://localhost:3000,http://localhost:5173`
- **Example**: `https://app.example.com,https://admin.example.com`
- **Description**: Allowed CORS origins. Set to your actual domains in production.

#### `CORS_ALLOW_CREDENTIALS`

- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Whether to allow credentials in CORS requests.

#### `CORS_ALLOWED_METHODS`

- **Type**: String (comma-separated)
- **Required**: No
- **Default**: `GET,POST,PUT,DELETE,OPTIONS`
- **Description**: Allowed HTTP methods for CORS.

#### `CORS_ALLOWED_HEADERS`

- **Type**: String (comma-separated)
- **Required**: No
- **Default**: `*`
- **Description**: Allowed headers for CORS. Use `*` for all or specify explicit headers.

---

### Logging Configuration

#### `LOG_LEVEL`

- **Type**: Enum
- **Required**: No
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Log level for the application.

#### `LOG_FORMAT`

- **Type**: Enum
- **Required**: No
- **Default**: `json`
- **Options**: `json`, `text`
- **Description**: Log format. JSON is recommended for production (easier to parse).

#### `LOG_REQUESTS`

- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Log all HTTP requests and responses.

#### `LOG_JWT_CLAIMS`

- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Warning**: DO NOT enable in production (exposes sensitive data)
- **Description**: Log decoded JWT claims for debugging.

---

### Performance and Scalability

#### `UVICORN_WORKERS`

- **Type**: Integer
- **Required**: No
- **Default**: `4`
- **Description**: Number of Uvicorn worker processes.
  Set to number of CPU cores for production.

#### `UVICORN_TIMEOUT`

- **Type**: Integer
- **Required**: No
- **Default**: `60`
- **Description**: Request timeout in seconds.

#### `MAX_REQUEST_SIZE_BYTES`

- **Type**: Integer
- **Required**: No
- **Default**: `10485760` (10 MB)
- **Description**: Maximum allowed request body size in bytes.

---

### Health Check Configuration

#### `ENABLE_HEALTH_CHECK`

- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable health check endpoints.

#### `HEALTH_CHECK_PATH`

- **Type**: String
- **Required**: No
- **Default**: `/health`
- **Description**: Path for health check endpoint.

#### `READINESS_CHECK_PATH`

- **Type**: String
- **Required**: No
- **Default**: `/ready`
- **Description**: Path for readiness check endpoint (for Kubernetes, ECS, etc.).

---

### Development / Testing Configuration

#### `DEBUG_MODE`

- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Warning**: DO NOT enable in production
- **Description**: Enable debug mode with verbose logging and error details.

#### `ENABLE_SWAGGER`

- **Type**: Boolean
- **Required**: No
- **Default**: `true`
- **Description**: Enable Swagger/OpenAPI documentation UI.

#### `SWAGGER_UI_PATH`

- **Type**: String
- **Required**: No
- **Default**: `/docs`
- **Description**: Path for Swagger UI.

#### `ENABLE_MOCK_AUTH`

- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Warning**: DO NOT enable in production
- **Description**: Enable mock authentication for testing without Entra ID.

---

### AWS-Specific Configuration

#### `AWS_REGION`

- **Type**: String
- **Required**: For AWS deployments
- **Default**: `us-east-1`
- **Description**: AWS region for ECS Fargate deployment.

#### `CLOUDWATCH_LOG_GROUP`

- **Type**: String
- **Required**: No
- **Default**: `/aws/ecs/mcp-server`
- **Description**: CloudWatch log group name.

#### `ENABLE_XRAY`

- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Description**: Enable AWS X-Ray distributed tracing.

---

### Agent Core Specific Configuration

#### `AGENTCORE_API_KEY`

- **Type**: String
- **Required**: For Agent Core deployments
- **Description**: API key for Agent Core (if required by your setup).

#### `AGENTCORE_PATH_PREFIX`

- **Type**: String
- **Required**: No
- **Example**: `/mcp`
- **Description**: Path prefix if CloudFront/proxy is rewriting URLs.

---

## Environment-Specific Examples

### Local Development

```bash
ENTRA_TENANT_ID=your-tenant-id
MCP_SERVER_APP_ID=api://mcp-server
MCP_SERVER_BASE_URL=http://localhost:8000
ENFORCE_HTTPS_REDIRECTS=false
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Production (AWS Fargate)

```bash
ENTRA_TENANT_ID=your-tenant-id
MCP_SERVER_APP_ID=api://mcp-server
MCP_SERVER_BASE_URL=https://mcp-server.example.com
DEPLOYMENT_MODE=fargate
ENFORCE_HTTPS_REDIRECTS=true
DEBUG_MODE=false
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_XRAY=true
CORS_ALLOWED_ORIGINS=https://app.example.com
```

### Production (Agent Core)

```bash
ENTRA_TENANT_ID=your-tenant-id
MCP_SERVER_APP_ID=api://mcp-server
MCP_SERVER_BASE_URL=https://agentcore.example.com/mcp
DEPLOYMENT_MODE=agentcore
AGENTCORE_PATH_PREFIX=/mcp
ENFORCE_HTTPS_REDIRECTS=true
DEBUG_MODE=false
LOG_LEVEL=INFO
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use secrets management** in production (AWS Secrets Manager, Azure Key Vault, etc.)
3. **Rotate client secrets** regularly
4. **Restrict CORS origins** to actual domains (not `*`)
5. **Keep `DEBUG_MODE` and `LOG_JWT_CLAIMS` disabled** in production
6. **Use HTTPS** in production (`ENFORCE_HTTPS_REDIRECTS=true`)
7. **Set appropriate log levels** (INFO or WARNING in production)
8. **Monitor and audit** access logs regularly

## Validation

The MCP server validates all required environment variables on startup
and will fail fast with clear error messages if any are missing or invalid.

To validate your configuration:

```bash
# Dry-run to check configuration
docker-compose config

# Start server and check logs
docker-compose up mcp-server
# Look for "Configuration loaded successfully" message
```
