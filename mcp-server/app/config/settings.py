"""Configuration settings for MCP server using Pydantic."""

import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Entra ID Configuration
    # -------------------------------------------------------------------------
    ENTRA_TENANT_ID: str = Field(..., description="Entra ID tenant ID")

    @property
    def ENTRA_AUTHORITY(self) -> str:
        """Construct authority URL from tenant ID."""
        return f"https://login.microsoftonline.com/{self.ENTRA_TENANT_ID}"

    @property
    def ENTRA_OIDC_CONFIG_URL(self) -> str:
        """Construct OIDC discovery URL."""
        return f"{self.ENTRA_AUTHORITY}/v2.0/.well-known/openid-configuration"

    @property
    def ENTRA_JWKS_URL(self) -> str:
        """Construct JWKS URL."""
        return f"{self.ENTRA_AUTHORITY}/discovery/v2.0/keys"

    # -------------------------------------------------------------------------
    # MCP Server Identity
    # -------------------------------------------------------------------------
    MCP_SERVER_APP_ID: str = Field(
        ..., description="MCP server app ID (audience claim in JWT)"
    )
    MCP_SERVER_SCOPE_PREFIX: Optional[str] = Field(
        None, description="Scope prefix (defaults to MCP_SERVER_APP_ID)"
    )

    @property
    def scope_prefix(self) -> str:
        """Get scope prefix, defaulting to app ID."""
        return self.MCP_SERVER_SCOPE_PREFIX or self.MCP_SERVER_APP_ID

    # -------------------------------------------------------------------------
    # Authorization Requirements
    # -------------------------------------------------------------------------
    REQUIRED_SCOPE: str = Field(
        ..., description="Required scope(s) for user tokens (space-separated)"
    )
    REQUIRED_SCOPES_ANY: Optional[str] = Field(
        None, description="Any of these scopes (comma-separated, OR logic)"
    )
    REQUIRED_SCOPES_ALL: Optional[str] = Field(
        None, description="All of these scopes (comma-separated, AND logic)"
    )

    REQUIRED_ROLE: str = Field(..., description="Required role for service principal tokens")
    REQUIRED_ROLES_ANY: Optional[str] = Field(
        None, description="Any of these roles (comma-separated, OR logic)"
    )

    def get_required_scopes(self) -> list[str]:
        """Get list of required scopes based on configuration."""
        if self.REQUIRED_SCOPES_ALL:
            return self.REQUIRED_SCOPES_ALL.split(",")
        if self.REQUIRED_SCOPES_ANY:
            return self.REQUIRED_SCOPES_ANY.split(",")
        return self.REQUIRED_SCOPE.split()

    def get_required_roles(self) -> list[str]:
        """Get list of required roles based on configuration."""
        if self.REQUIRED_ROLES_ANY:
            return self.REQUIRED_ROLES_ANY.split(",")
        return [self.REQUIRED_ROLE]

    def validate_scopes_all(self) -> bool:
        """Check if all scopes are required (AND logic)."""
        return bool(self.REQUIRED_SCOPES_ALL)

    def validate_roles_any(self) -> bool:
        """Check if any role is sufficient (OR logic)."""
        return bool(self.REQUIRED_ROLES_ANY)

    # -------------------------------------------------------------------------
    # Pre-registered Client IDs
    # -------------------------------------------------------------------------
    VSCODE_CLIENT_ID: str = Field(..., description="VS Code MCP client ID")
    CLAUDE_DESKTOP_CLIENT_ID: str = Field(..., description="Claude Desktop MCP client ID")
    CLAUDE_CODE_CLIENT_ID: str = Field(..., description="Claude Code MCP client ID")
    CHATGPT_CLIENT_ID: str = Field(..., description="ChatGPT MCP client ID")
    GENERIC_CLIENT_ID: str = Field(..., description="Generic/fallback MCP client ID")

    CONFIDENTIAL_CLIENT_ID: Optional[str] = Field(
        None, description="Confidential client ID (for testing)"
    )
    CONFIDENTIAL_CLIENT_SECRET: Optional[str] = Field(
        None, description="Confidential client secret (for testing)"
    )

    SERVICE_PRINCIPAL_CLIENT_ID: Optional[str] = Field(
        None, description="Service principal client ID (for testing)"
    )
    SERVICE_PRINCIPAL_CLIENT_SECRET: Optional[str] = Field(
        None, description="Service principal client secret (for testing)"
    )

    # -------------------------------------------------------------------------
    # MCP Server Configuration
    # -------------------------------------------------------------------------
    DEPLOYMENT_MODE: Literal["fargate", "agentcore"] = Field(
        default="fargate", description="Deployment mode"
    )
    MCP_SERVER_HOST: str = Field(default="0.0.0.0", description="Server host")
    MCP_SERVER_PORT: int = Field(default=8000, description="Server port")
    MCP_SERVER_BASE_URL: str = Field(
        default="http://localhost:8000", description="Public base URL"
    )

    # -------------------------------------------------------------------------
    # JWT Validation Configuration
    # -------------------------------------------------------------------------
    JWT_CLOCK_SKEW_SECONDS: int = Field(
        default=300, description="Clock skew tolerance (5 minutes)"
    )
    JWKS_CACHE_TTL_SECONDS: int = Field(
        default=86400, description="JWKS cache TTL (24 hours)"
    )
    VALIDATE_TOKEN_VERSION: bool = Field(default=True, description="Validate token version")
    ALLOWED_TOKEN_VERSIONS: str = Field(default="2.0", description="Allowed token versions")
    ENFORCE_HTTPS_REDIRECTS: bool = Field(
        default=False, description="Enforce HTTPS for redirect URIs"
    )

    def get_allowed_token_versions(self) -> list[str]:
        """Get list of allowed token versions."""
        return [v.strip() for v in self.ALLOWED_TOKEN_VERSIONS.split(",")]

    # -------------------------------------------------------------------------
    # Token Revocation (Optional)
    # -------------------------------------------------------------------------
    ENABLE_TOKEN_REVOCATION: bool = Field(default=False, description="Enable token revocation")
    REDIS_URL: Optional[str] = Field(None, description="Redis connection string")
    REDIS_PASSWORD: Optional[str] = Field(None, description="Redis password")
    REVOCATION_CACHE_TTL_SECONDS: int = Field(
        default=3600, description="Revocation cache TTL"
    )

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: Optional[str], info) -> Optional[str]:
        """Validate Redis URL if revocation is enabled."""
        if info.data.get("ENABLE_TOKEN_REVOCATION") and not v:
            raise ValueError("REDIS_URL is required when ENABLE_TOKEN_REVOCATION is True")
        return v

    # -------------------------------------------------------------------------
    # DCR Emulation
    # -------------------------------------------------------------------------
    ENABLE_DCR_ENDPOINT: bool = Field(default=True, description="Enable DCR endpoint")
    DCR_RATE_LIMIT_PER_MINUTE: int = Field(
        default=10, description="DCR rate limit per IP per minute"
    )

    # -------------------------------------------------------------------------
    # Security Configuration
    # -------------------------------------------------------------------------
    CORS_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="CORS allowed origins",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS allow credentials")
    CORS_ALLOWED_METHODS: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS", description="CORS allowed methods"
    )
    CORS_ALLOWED_HEADERS: str = Field(default="*", description="CORS allowed headers")

    def get_cors_origins(self) -> list[str]:
        """Get list of CORS allowed origins."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",")]

    def get_cors_methods(self) -> list[str]:
        """Get list of CORS allowed methods."""
        return [method.strip() for method in self.CORS_ALLOWED_METHODS.split(",")]

    # -------------------------------------------------------------------------
    # Logging Configuration
    # -------------------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
    LOG_FORMAT: Literal["json", "text"] = Field(default="json", description="Log format")
    LOG_REQUESTS: bool = Field(default=True, description="Log HTTP requests")
    LOG_JWT_CLAIMS: bool = Field(
        default=False, description="Log JWT claims (DO NOT enable in production)"
    )

    # -------------------------------------------------------------------------
    # Performance & Scalability
    # -------------------------------------------------------------------------
    UVICORN_WORKERS: int = Field(default=4, description="Number of Uvicorn workers")
    UVICORN_TIMEOUT: int = Field(default=60, description="Request timeout in seconds")
    MAX_REQUEST_SIZE_BYTES: int = Field(
        default=10485760, description="Max request size (10MB)"
    )

    # -------------------------------------------------------------------------
    # Health Check Configuration
    # -------------------------------------------------------------------------
    ENABLE_HEALTH_CHECK: bool = Field(default=True, description="Enable health check")
    HEALTH_CHECK_PATH: str = Field(default="/health", description="Health check path")
    READINESS_CHECK_PATH: str = Field(default="/ready", description="Readiness check path")

    # -------------------------------------------------------------------------
    # Development / Testing Configuration
    # -------------------------------------------------------------------------
    DEBUG_MODE: bool = Field(default=False, description="Debug mode (DO NOT enable in prod)")
    ENABLE_SWAGGER: bool = Field(default=True, description="Enable Swagger UI")
    SWAGGER_UI_PATH: str = Field(default="/docs", description="Swagger UI path")
    ENABLE_MOCK_AUTH: bool = Field(
        default=False, description="Mock auth (DO NOT enable in prod)"
    )

    # -------------------------------------------------------------------------
    # AWS-Specific Configuration
    # -------------------------------------------------------------------------
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    CLOUDWATCH_LOG_GROUP: str = Field(
        default="/aws/ecs/mcp-server", description="CloudWatch log group"
    )
    ENABLE_XRAY: bool = Field(default=False, description="Enable AWS X-Ray")

    # -------------------------------------------------------------------------
    # Agent Core Specific Configuration
    # -------------------------------------------------------------------------
    AGENTCORE_API_KEY: Optional[str] = Field(None, description="Agent Core API key")
    AGENTCORE_PATH_PREFIX: Optional[str] = Field(
        None, description="Agent Core path prefix"
    )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    @field_validator("LOG_JWT_CLAIMS")
    @classmethod
    def validate_log_jwt_claims(cls, v: bool, info) -> bool:
        """Warn if JWT claims logging is enabled in production."""
        if v and not info.data.get("DEBUG_MODE"):
            import warnings

            warnings.warn(
                "LOG_JWT_CLAIMS is enabled without DEBUG_MODE. "
                "This exposes sensitive data and should NOT be used in production.",
                UserWarning,
            )
        return v

    @field_validator("DEBUG_MODE")
    @classmethod
    def validate_debug_mode(cls, v: bool) -> bool:
        """Warn if debug mode is enabled."""
        if v:
            import warnings

            warnings.warn(
                "DEBUG_MODE is enabled. This should NOT be used in production.",
                UserWarning,
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache to ensure settings are loaded once and reused.
    """
    return Settings()
