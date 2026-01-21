"""Pytest fixtures and configuration for MCP server tests."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Set test environment variables before importing app
os.environ.update({
    "ENTRA_TENANT_ID": "test-tenant-id",
    "MCP_SERVER_APP_ID": "api://test-mcp-server",
    "REQUIRED_SCOPE": "test.read test.write",
    "REQUIRED_ROLE": "Test.ReadWrite.All",
    "VSCODE_CLIENT_ID": "vscode-client-id",
    "CLAUDE_DESKTOP_CLIENT_ID": "claude-desktop-client-id",
    "CLAUDE_CODE_CLIENT_ID": "claude-code-client-id",
    "CHATGPT_CLIENT_ID": "chatgpt-client-id",
    "GENERIC_CLIENT_ID": "generic-client-id",
    "ENABLE_MOCK_AUTH": "false",
    "ENABLE_DCR_ENDPOINT": "true",
    "LOG_LEVEL": "ERROR",  # Suppress logs during tests
})

from app.config import Settings, get_settings
from app.main import create_app


# ============================================================================
# Settings Fixtures
# ============================================================================

@pytest.fixture
def test_settings() -> Settings:
    """Get test settings."""
    return get_settings()


@pytest.fixture
def mock_settings() -> Settings:
    """Get mock settings for testing."""
    return Settings(
        ENTRA_TENANT_ID="test-tenant-id",
        MCP_SERVER_APP_ID="api://test-mcp-server",
        REQUIRED_SCOPE="test.read test.write",
        REQUIRED_ROLE="Test.ReadWrite.All",
        VSCODE_CLIENT_ID="vscode-client-id",
        CLAUDE_DESKTOP_CLIENT_ID="claude-desktop-client-id",
        CLAUDE_CODE_CLIENT_ID="claude-code-client-id",
        CHATGPT_CLIENT_ID="chatgpt-client-id",
        GENERIC_CLIENT_ID="generic-client-id",
    )


# ============================================================================
# JWT & JWKS Fixtures
# ============================================================================

@pytest.fixture
def private_key() -> str:
    """Generate RSA private key for testing."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')


@pytest.fixture
def public_key(private_key: str) -> str:
    """Get public key from private key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    key = serialization.load_pem_private_key(
        private_key.encode(),
        password=None,
        backend=default_backend()
    )

    public = key.public_key()
    return public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')


@pytest.fixture
def jwks_response() -> Dict[str, Any]:
    """Mock JWKS response from Entra ID."""
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-key-id-1",
                "x5t": "test-thumbprint",
                "n": "test-modulus",
                "e": "AQAB",
                "x5c": ["test-cert"],
                "issuer": "https://login.microsoftonline.com/test-tenant-id/v2.0"
            }
        ]
    }


@pytest.fixture
def user_jwt_claims(test_settings: Settings) -> Dict[str, Any]:
    """User (delegated) JWT claims."""
    now = datetime.now(timezone.utc)
    return {
        "aud": test_settings.MCP_SERVER_APP_ID,
        "iss": f"{test_settings.ENTRA_AUTHORITY}/v2.0",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "sub": "test-user-subject",
        "oid": "test-user-oid",
        "tid": test_settings.ENTRA_TENANT_ID,
        "preferred_username": "testuser@example.com",
        "name": "Test User",
        "scp": "test.read test.write",
        "ver": "2.0",
        "appid": "test-client-id",
        "azp": "test-client-id",
    }


@pytest.fixture
def app_only_jwt_claims(test_settings: Settings) -> Dict[str, Any]:
    """App-only (service principal) JWT claims."""
    now = datetime.now(timezone.utc)
    return {
        "aud": test_settings.MCP_SERVER_APP_ID,
        "iss": f"{test_settings.ENTRA_AUTHORITY}/v2.0",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "sub": "test-sp-oid",
        "oid": "test-sp-oid",
        "tid": test_settings.ENTRA_TENANT_ID,
        "roles": ["Test.ReadWrite.All"],
        "idtyp": "app",
        "ver": "2.0",
        "appid": "test-sp-client-id",
        "azp": "test-sp-client-id",
        "app_displayname": "Test Service Principal",
    }


@pytest.fixture
def expired_jwt_claims(user_jwt_claims: Dict[str, Any]) -> Dict[str, Any]:
    """Expired JWT claims."""
    expired = user_jwt_claims.copy()
    now = datetime.now(timezone.utc)
    expired["exp"] = int((now - timedelta(hours=1)).timestamp())
    expired["iat"] = int((now - timedelta(hours=2)).timestamp())
    return expired


@pytest.fixture
def create_jwt_token(private_key: str):
    """Factory fixture to create JWT tokens."""
    def _create_token(
        claims: Dict[str, Any],
        kid: str = "test-key-id-1",
        algorithm: str = "RS256"
    ) -> str:
        """Create a signed JWT token.

        Args:
            claims: JWT claims
            kid: Key ID
            algorithm: Signing algorithm

        Returns:
            Signed JWT token
        """
        headers = {"kid": kid}
        return jwt.encode(claims, private_key, algorithm=algorithm, headers=headers)

    return _create_token


@pytest.fixture
def valid_user_token(user_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """Valid user JWT token."""
    return create_jwt_token(user_jwt_claims)


@pytest.fixture
def valid_app_token(app_only_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """Valid app-only JWT token."""
    return create_jwt_token(app_only_jwt_claims)


@pytest.fixture
def expired_token(expired_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """Expired JWT token."""
    return create_jwt_token(expired_jwt_claims)


# ============================================================================
# HTTP Client Fixtures
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for JWKS fetching."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-key-id-1",
                "n": "test-modulus",
                "e": "AQAB",
            }
        ]
    }
    client.get.return_value = response
    return client


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async FastAPI test client."""
    from httpx import AsyncClient
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Auth Fixtures
# ============================================================================

@pytest.fixture
def auth_headers(valid_user_token: str) -> Dict[str, str]:
    """Authorization headers with valid user token."""
    return {"Authorization": f"Bearer {valid_user_token}"}


@pytest.fixture
def app_auth_headers(valid_app_token: str) -> Dict[str, str]:
    """Authorization headers with valid app token."""
    return {"Authorization": f"Bearer {valid_app_token}"}


# ============================================================================
# DCR Fixtures
# ============================================================================

@pytest.fixture
def vscode_dcr_request() -> Dict[str, Any]:
    """VS Code DCR request."""
    return {
        "redirect_uris": ["vscode://mcp-auth/callback"],
        "client_name": "VS Code MCP Client",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }


@pytest.fixture
def claude_code_dcr_request() -> Dict[str, Any]:
    """Claude Code DCR request."""
    return {
        "redirect_uris": ["http://localhost:8080/callback"],
        "client_name": "Claude Code",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }


@pytest.fixture
def vscode_user_agent() -> Dict[str, str]:
    """VS Code User-Agent header."""
    return {"User-Agent": "VSCode-MCP/1.0"}


@pytest.fixture
def claude_code_user_agent() -> Dict[str, str]:
    """Claude Code User-Agent header."""
    return {"User-Agent": "Claude-CLI/1.0"}


# ============================================================================
# Mock Fixtures for External Dependencies
# ============================================================================

@pytest.fixture
def mock_jwks_cache(public_key: str, jwks_response: Dict[str, Any]):
    """Mock JWKS cache."""
    from unittest.mock import AsyncMock
    from app.auth.jwks_cache import JWKSCache

    cache = AsyncMock(spec=JWKSCache)
    cache.get_jwks.return_value = jwks_response
    cache.get_key_by_kid.return_value = jwks_response["keys"][0]
    return cache


# ============================================================================
# Test Data Helpers
# ============================================================================

@pytest.fixture
def invalid_token() -> str:
    """Invalid JWT token (malformed)."""
    return "invalid.jwt.token"


@pytest.fixture
def token_without_kid(user_jwt_claims: Dict[str, Any], private_key: str) -> str:
    """JWT token without kid header."""
    return jwt.encode(user_jwt_claims, private_key, algorithm="RS256")


@pytest.fixture
def token_wrong_issuer(user_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """JWT token with wrong issuer."""
    claims = user_jwt_claims.copy()
    claims["iss"] = "https://wrong-issuer.com"
    return create_jwt_token(claims)


@pytest.fixture
def token_wrong_audience(user_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """JWT token with wrong audience."""
    claims = user_jwt_claims.copy()
    claims["aud"] = "wrong-audience"
    return create_jwt_token(claims)


@pytest.fixture
def token_missing_scope(user_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """User token with insufficient scope."""
    claims = user_jwt_claims.copy()
    claims["scp"] = "other.scope"
    return create_jwt_token(claims)


@pytest.fixture
def token_missing_role(app_only_jwt_claims: Dict[str, Any], create_jwt_token) -> str:
    """App-only token with insufficient role."""
    claims = app_only_jwt_claims.copy()
    claims["roles"] = ["Other.Role"]
    return create_jwt_token(claims)
