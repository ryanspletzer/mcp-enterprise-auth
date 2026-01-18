"""Pytest fixtures for mock Entra ID tests."""

import secrets
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.crypto.jwt_issuer import JWTIssuer
from app.crypto.key_manager import KeyManager
from app.main import create_app
from app.storage.memory import InMemoryStorage


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with known values."""
    return Settings(
        MOCK_TENANT_ID="test-tenant-id",
        MOCK_IDP_HOST="localhost",
        MOCK_IDP_PORT=8001,
        MOCK_IDP_BASE_URL="http://localhost:8001",
        ACCESS_TOKEN_TTL=3600,
        REFRESH_TOKEN_TTL=86400,
        AUTH_CODE_TTL=600,
        MCP_SERVER_APP_ID="api://test-mcp-server",
        DEFAULT_SCOPE="api://test-mcp-server/.default",
        TEST_USERS="testuser@example.com,admin@example.com",
        VSCODE_CLIENT_ID="test-vscode-client",
        CLAUDE_CODE_CLIENT_ID="test-claude-client",
        CONFIDENTIAL_CLIENT_ID="test-confidential-client",
        CONFIDENTIAL_CLIENT_SECRET="test-secret",
        SERVICE_PRINCIPAL_CLIENT_ID="test-sp-client",
        SERVICE_PRINCIPAL_CLIENT_SECRET="test-sp-secret",
        LOG_LEVEL="INFO",
        LOG_FORMAT="console",
        STORAGE_BACKEND="memory",
    )


@pytest.fixture
def key_manager() -> KeyManager:
    """Key manager instance for tests."""
    return KeyManager()


@pytest.fixture
def jwt_issuer(test_settings: Settings, key_manager: KeyManager) -> JWTIssuer:
    """JWT issuer instance for tests."""
    return JWTIssuer(test_settings, key_manager)


@pytest.fixture
def storage(test_settings: Settings) -> InMemoryStorage:
    """In-memory storage instance for tests."""
    return InMemoryStorage(test_settings)


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    app = create_app()
    return TestClient(app)


# PKCE fixtures
@pytest.fixture
def code_verifier() -> str:
    """Generate PKCE code verifier."""
    return secrets.token_urlsafe(32)


@pytest.fixture
def code_challenge(code_verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    import hashlib
    import base64

    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


# Test user fixtures
@pytest.fixture
def test_user_id() -> str:
    """Test user ID."""
    return "test-user-oid"


@pytest.fixture
def test_username() -> str:
    """Test username."""
    return "testuser@example.com"


@pytest.fixture
def test_user_name() -> str:
    """Test user display name."""
    return "Test User"


# Test client fixtures
@pytest.fixture
def public_client_id(test_settings: Settings) -> str:
    """Public client ID."""
    return test_settings.CLAUDE_CODE_CLIENT_ID


@pytest.fixture
def confidential_client_id(test_settings: Settings) -> str:
    """Confidential client ID."""
    return test_settings.CONFIDENTIAL_CLIENT_ID


@pytest.fixture
def confidential_client_secret(test_settings: Settings) -> str:
    """Confidential client secret."""
    return test_settings.CONFIDENTIAL_CLIENT_SECRET


@pytest.fixture
def service_principal_client_id(test_settings: Settings) -> str:
    """Service principal client ID."""
    return test_settings.SERVICE_PRINCIPAL_CLIENT_ID


@pytest.fixture
def service_principal_client_secret(test_settings: Settings) -> str:
    """Service principal client secret."""
    return test_settings.SERVICE_PRINCIPAL_CLIENT_SECRET


# OAuth flow fixtures
@pytest.fixture
def redirect_uri() -> str:
    """Test redirect URI."""
    return "http://localhost:8080/callback"


@pytest.fixture
def scope(test_settings: Settings) -> str:
    """Test scope."""
    return test_settings.DEFAULT_SCOPE


@pytest.fixture
def state() -> str:
    """OAuth state parameter."""
    return secrets.token_urlsafe(16)
