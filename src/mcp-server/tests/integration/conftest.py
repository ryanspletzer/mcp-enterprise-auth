"""Pytest fixtures for integration tests with mock Entra ID.

These fixtures create tokens using the same crypto modules as the mock IdP,
allowing us to test MCP server's token validation end-to-end without needing
to run both servers in the same process.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt

# Shared configuration
SHARED_TENANT_ID = "integration-test-tenant"
SHARED_APP_ID = "api://integration-test-mcp-server"
SHARED_ISSUER = f"http://localhost:8001/{SHARED_TENANT_ID}/v2.0"

# Test key ID
TEST_KEY_ID = "integration-test-key-1"


# =============================================================================
# Cryptographic Key Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def rsa_private_key():
    """Generate RSA private key for signing tokens."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )


@pytest.fixture(scope="module")
def rsa_private_key_pem(rsa_private_key) -> str:
    """Get PEM-encoded private key."""
    return rsa_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


@pytest.fixture(scope="module")
def rsa_public_key_jwk(rsa_private_key) -> Dict[str, Any]:
    """Get public key in JWK format for JWKS endpoint."""
    import base64

    public_key = rsa_private_key.public_key()
    public_numbers = public_key.public_numbers()

    # Convert to base64url encoding (no padding)
    def to_base64url(num: int, length: int) -> str:
        return (
            base64.urlsafe_b64encode(num.to_bytes(length, byteorder="big"))
            .decode("ascii")
            .rstrip("=")
        )

    # RSA modulus and exponent
    n = to_base64url(public_numbers.n, 256)  # 2048-bit key = 256 bytes
    e = to_base64url(public_numbers.e, 3)  # exponent is typically small

    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": TEST_KEY_ID,
        "n": n,
        "e": e,
    }


@pytest.fixture(scope="module")
def mock_jwks(rsa_public_key_jwk: Dict[str, Any]) -> Dict[str, Any]:
    """Mock JWKS response containing our test public key."""
    return {"keys": [rsa_public_key_jwk]}


# =============================================================================
# Token Generation Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def create_access_token(rsa_private_key_pem: str):
    """Factory fixture to create signed JWT access tokens."""

    def _create_token(
        subject: str = "test-subject",
        client_id: str = "test-client-id",
        scopes: str | None = None,
        roles: list[str] | None = None,
        is_app_token: bool = False,
        expires_in: int = 3600,
        extra_claims: Dict[str, Any] | None = None,
    ) -> str:
        """Create a signed JWT token.

        Args:
            subject: Token subject (user OID or app OID)
            client_id: Client/app ID that requested the token
            scopes: Space-separated scopes (for user tokens)
            roles: List of roles (for app tokens)
            is_app_token: Whether this is an app-only token
            expires_in: Token lifetime in seconds
            extra_claims: Additional claims to include

        Returns:
            Signed JWT access token
        """
        now = datetime.now(timezone.utc)

        claims = {
            "aud": SHARED_APP_ID,
            "iss": SHARED_ISSUER,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
            "sub": subject,
            "oid": subject,
            "tid": SHARED_TENANT_ID,
            "ver": "2.0",
            "azp": client_id,
            "appid": client_id,
        }

        if is_app_token:
            claims["idtyp"] = "app"
            claims["roles"] = roles or ["MCP.ReadWrite.All"]
        else:
            claims["scp"] = scopes or "mcp.read mcp.write"
            claims["preferred_username"] = "testuser@example.com"
            claims["name"] = "Test User"

        if extra_claims:
            claims.update(extra_claims)

        return jwt.encode(
            claims,
            rsa_private_key_pem,
            algorithm="RS256",
            headers={"kid": TEST_KEY_ID},
        )

    return _create_token


@pytest.fixture
def valid_user_token(create_access_token) -> str:
    """Valid user (delegated) access token."""
    return create_access_token(
        subject="test-user-oid",
        client_id="test-client-id",
        scopes="mcp.read mcp.write",
        is_app_token=False,
    )


@pytest.fixture
def valid_app_token(create_access_token) -> str:
    """Valid app-only (service principal) access token."""
    return create_access_token(
        subject="test-sp-oid",
        client_id="test-sp-client-id",
        roles=["MCP.ReadWrite.All"],
        is_app_token=True,
    )


@pytest.fixture
def expired_token(create_access_token) -> str:
    """Expired access token."""
    return create_access_token(
        subject="test-user-oid",
        expires_in=-3600,  # Expired 1 hour ago
    )


@pytest.fixture
def token_wrong_audience(rsa_private_key_pem: str) -> str:
    """Token with wrong audience."""
    now = datetime.now(timezone.utc)
    claims = {
        "aud": "wrong-audience",
        "iss": SHARED_ISSUER,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "sub": "test-user-oid",
        "tid": SHARED_TENANT_ID,
        "scp": "mcp.read mcp.write",
        "ver": "2.0",
    }
    return jwt.encode(claims, rsa_private_key_pem, algorithm="RS256", headers={"kid": TEST_KEY_ID})


@pytest.fixture
def token_wrong_tenant(rsa_private_key_pem: str) -> str:
    """Token from wrong tenant."""
    now = datetime.now(timezone.utc)
    claims = {
        "aud": SHARED_APP_ID,
        "iss": "http://localhost:8001/wrong-tenant/v2.0",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "sub": "test-user-oid",
        "tid": "wrong-tenant-id",
        "scp": "mcp.read mcp.write",
        "ver": "2.0",
    }
    return jwt.encode(claims, rsa_private_key_pem, algorithm="RS256", headers={"kid": TEST_KEY_ID})


# =============================================================================
# MCP Server Test Client Fixtures
# =============================================================================


@pytest.fixture
def integration_mcp_settings() -> Dict[str, str]:
    """Environment settings for MCP server integration tests."""
    return {
        "ENTRA_TENANT_ID": SHARED_TENANT_ID,
        "ENTRA_AUTHORITY": "http://localhost:8001",
        "ENTRA_JWKS_URL": "http://localhost:8001/discovery/v2.0/keys",
        "MCP_SERVER_APP_ID": SHARED_APP_ID,
        "MCP_SERVER_SCOPE_PREFIX": SHARED_APP_ID,
        "REQUIRED_SCOPE": "mcp.read mcp.write",
        "REQUIRED_ROLE": "MCP.ReadWrite.All",
        "VSCODE_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
        "CLAUDE_DESKTOP_CLIENT_ID": "22222222-2222-2222-2222-222222222222",
        "CLAUDE_CODE_CLIENT_ID": "33333333-3333-3333-3333-333333333333",
        "CHATGPT_CLIENT_ID": "44444444-4444-4444-4444-444444444444",
        "GENERIC_CLIENT_ID": "55555555-5555-5555-5555-555555555555",
        "ENABLE_MOCK_AUTH": "false",
        "ENABLE_DCR_ENDPOINT": "true",
        "LOG_LEVEL": "WARNING",
    }


@pytest.fixture
def mcp_client_with_mock_jwks(
    mock_jwks: Dict[str, Any],
    integration_mcp_settings: Dict[str, str],
) -> Generator[TestClient, None, None]:
    """Create MCP server test client with mocked JWKS.

    This fixture configures the MCP server to use our test keys for
    token validation, allowing end-to-end auth testing.
    """
    from unittest.mock import AsyncMock, patch

    # Save and update environment
    original_env = os.environ.copy()
    os.environ.update(integration_mcp_settings)

    # Clear the settings cache to pick up new env vars
    from app.config import get_settings

    get_settings.cache_clear()

    try:
        # Create mock JWKS cache
        mock_cache = AsyncMock()
        mock_cache.get_jwks.return_value = mock_jwks

        # Return the correct key when looking up by kid
        async def get_key_by_kid(kid: str):
            for key in mock_jwks["keys"]:
                if key.get("kid") == kid:
                    return key
            return None

        mock_cache.get_key_by_kid = AsyncMock(side_effect=get_key_by_kid)

        # Mock the JWKS cache in middleware (where it's imported and used)
        # The middleware creates AuthMiddleware which creates JWKSCache
        with patch("app.auth.middleware.JWKSCache") as MockJWKSCache:
            MockJWKSCache.return_value = mock_cache

            from app.main import create_app

            # Create the app inside the patch context
            app = create_app()

            with TestClient(app) as client:
                yield client
    finally:
        # Restore environment and clear cache
        os.environ.clear()
        os.environ.update(original_env)
        get_settings.cache_clear()


# =============================================================================
# Helper Fixtures
# =============================================================================


@pytest.fixture
def auth_headers(valid_user_token: str) -> Dict[str, str]:
    """Authorization headers with valid user token."""
    return {"Authorization": f"Bearer {valid_user_token}"}


@pytest.fixture
def app_auth_headers(valid_app_token: str) -> Dict[str, str]:
    """Authorization headers with valid app token."""
    return {"Authorization": f"Bearer {valid_app_token}"}
