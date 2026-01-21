"""Configuration settings for Mock Entra ID.

WARNING: This mock IdP is for TESTING and DEVELOPMENT only.
It MUST NOT be used in production environments.
"""

import warnings
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Mock Entra ID configuration settings.

    WARNING: This mock IdP is for testing and development only.
    Do NOT use in production - use actual Microsoft Entra ID.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment Configuration - prevents accidental production use
    ENVIRONMENT: Literal["test", "development", "local"] = Field(
        default="development",
        description="Environment mode - MUST be test, development, or local (NOT production)",
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Prevent running in production-like environments."""
        if v.lower() in ("production", "prod", "live", "staging"):
            raise ValueError(
                "Mock IdP MUST NOT be used in production or staging environments. "
                "Use actual Microsoft Entra ID for production deployments."
            )
        # Always warn that this is a mock IdP
        warnings.warn(
            f"Mock Entra ID is running in '{v}' mode. "
            "This is for TESTING ONLY - do NOT use in production.",
            UserWarning,
            stacklevel=2,
        )
        return v

    # Mock IdP Configuration
    MOCK_TENANT_ID: str = Field(
        default="12345678-1234-1234-1234-123456789abc",
        description="Mock tenant ID for token claims",
    )
    MOCK_IDP_HOST: str = Field(
        default="0.0.0.0",
        description="Host to bind the mock IdP server",
    )
    MOCK_IDP_PORT: int = Field(
        default=8001,
        description="Port for the mock IdP server",
    )
    MOCK_IDP_BASE_URL: str = Field(
        default="http://localhost:8001",
        description="Base URL for the mock IdP",
    )

    # Token Configuration
    ACCESS_TOKEN_TTL: int = Field(
        default=3600,
        description="Access token lifetime in seconds (default: 1 hour)",
    )
    REFRESH_TOKEN_TTL: int = Field(
        default=86400,
        description="Refresh token lifetime in seconds (default: 24 hours)",
    )
    AUTH_CODE_TTL: int = Field(
        default=600,
        description="Authorization code lifetime in seconds (default: 10 minutes)",
    )

    # MCP Server Configuration
    MCP_SERVER_APP_ID: str = Field(
        default="api://mcp-server",
        description="Default audience claim for issued tokens",
    )
    DEFAULT_SCOPE: str = Field(
        default="api://mcp-server/.default",
        description="Default scope for authorization",
    )

    # Pre-seeded Test Users
    TEST_USERS: str = Field(
        default="testuser@example.com,admin@example.com,demo@example.com",
        description="Comma-separated list of pre-registered test users",
    )

    # Pre-registered Clients
    VSCODE_CLIENT_ID: str = Field(
        default="11111111-1111-1111-1111-111111111111",
        description="VS Code extension client ID",
    )
    CLAUDE_CODE_CLIENT_ID: str = Field(
        default="33333333-3333-3333-3333-333333333333",
        description="Claude Code CLI client ID",
    )
    CONFIDENTIAL_CLIENT_ID: str = Field(
        default="66666666-6666-6666-6666-666666666666",
        description="Confidential client ID",
    )
    CONFIDENTIAL_CLIENT_SECRET: str = Field(
        default="test-secret-123",
        description="Confidential client secret",
    )
    SERVICE_PRINCIPAL_CLIENT_ID: str = Field(
        default="77777777-7777-7777-7777-777777777777",
        description="Service principal client ID",
    )
    SERVICE_PRINCIPAL_CLIENT_SECRET: str = Field(
        default="test-sp-secret-456",
        description="Service principal client secret",
    )

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    LOG_FORMAT: Literal["json", "console"] = Field(
        default="json",
        description="Log output format",
    )

    # Storage Backend
    STORAGE_BACKEND: Literal["memory", "redis"] = Field(
        default="memory",
        description="Storage backend for sessions and tokens",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Redis connection URL (if using Redis backend)",
    )

    @property
    def issuer(self) -> str:
        """Get the token issuer URL (using mock IdP base URL)."""
        return f"{self.MOCK_IDP_BASE_URL}/v2.0"

    @property
    def authorization_endpoint(self) -> str:
        """Get the authorization endpoint URL."""
        return f"{self.MOCK_IDP_BASE_URL}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        """Get the token endpoint URL."""
        return f"{self.MOCK_IDP_BASE_URL}/oauth2/v2.0/token"

    @property
    def jwks_uri(self) -> str:
        """Get the JWKS endpoint URL."""
        return f"{self.MOCK_IDP_BASE_URL}/discovery/v2.0/keys"

    def get_test_users(self) -> list[str]:
        """Get list of test users."""
        return [u.strip() for u in self.TEST_USERS.split(",") if u.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
