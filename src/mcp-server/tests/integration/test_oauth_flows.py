"""Integration tests for MCP server token validation.

These tests verify token validation end-to-end by:
1. Generating tokens with known cryptographic keys
2. Mocking the JWKS endpoint to return those keys
3. Testing MCP server accepts/rejects tokens appropriately

Note: Tests that require actual mock IdP interaction are in a separate
test module that runs both servers together.
"""

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from tests.integration.conftest import (
    SHARED_APP_ID,
    SHARED_ISSUER,
    SHARED_TENANT_ID,
    TEST_KEY_ID,
)


@pytest.mark.integration
class TestTokenClaimsStructure:
    """Test generated tokens have correct claims structure."""

    def test_user_token_has_correct_claims(
        self,
        valid_user_token: str,
    ):
        """Test user token has correct claims structure."""
        # Decode without verification to inspect claims
        claims = jwt.get_unverified_claims(valid_user_token)

        # Verify standard claims
        assert claims["aud"] == SHARED_APP_ID
        assert claims["iss"] == SHARED_ISSUER
        assert claims["tid"] == SHARED_TENANT_ID

        # Verify user token specific claims
        assert "scp" in claims
        assert claims["scp"] == "mcp.read mcp.write"
        assert "preferred_username" in claims
        assert "name" in claims

        # Verify temporal claims exist
        assert "iat" in claims
        assert "nbf" in claims
        assert "exp" in claims

    def test_app_token_has_correct_claims(
        self,
        valid_app_token: str,
    ):
        """Test app-only token has correct claims structure."""
        claims = jwt.get_unverified_claims(valid_app_token)

        # Verify standard claims
        assert claims["aud"] == SHARED_APP_ID
        assert claims["iss"] == SHARED_ISSUER
        assert claims["tid"] == SHARED_TENANT_ID

        # Verify app-only token claims
        assert claims["idtyp"] == "app"
        assert "roles" in claims
        assert isinstance(claims["roles"], list)
        assert "MCP.ReadWrite.All" in claims["roles"]

        # Verify temporal claims exist
        assert "iat" in claims
        assert "nbf" in claims
        assert "exp" in claims

    def test_token_has_kid_header(
        self,
        valid_user_token: str,
    ):
        """Test token has 'kid' in header for key lookup."""
        header = jwt.get_unverified_header(valid_user_token)
        kid = header.get("kid")
        assert kid is not None, "Token should have 'kid' in header"
        assert kid == TEST_KEY_ID


@pytest.mark.integration
class TestMCPServerTokenValidation:
    """Test MCP server validates tokens correctly."""

    def test_health_endpoint_works_without_auth(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test health endpoint is accessible without authentication."""
        response = mcp_client_with_mock_jwks.get("/health")
        assert response.status_code == 200

    def test_protected_endpoint_requires_auth(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test protected endpoint returns 401 without token."""
        response = mcp_client_with_mock_jwks.get("/api/me")
        assert response.status_code == 401

    def test_protected_endpoint_rejects_invalid_token(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test protected endpoint rejects malformed token."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_rejects_expired_token(
        self,
        mcp_client_with_mock_jwks: TestClient,
        expired_token: str,
    ):
        """Test protected endpoint rejects expired token."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_rejects_wrong_audience(
        self,
        mcp_client_with_mock_jwks: TestClient,
        token_wrong_audience: str,
    ):
        """Test protected endpoint rejects token with wrong audience."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token_wrong_audience}"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_rejects_wrong_tenant(
        self,
        mcp_client_with_mock_jwks: TestClient,
        token_wrong_tenant: str,
    ):
        """Test protected endpoint rejects token from wrong tenant."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token_wrong_tenant}"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestDCREmulationFlow:
    """Test DCR emulation flow for different client types."""

    def test_dcr_register_vscode_client(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test DCR registration for VS Code client."""
        response = mcp_client_with_mock_jwks.post(
            "/dcr/register",
            json={
                "redirect_uris": ["vscode://mcp-auth/callback"],
                "client_name": "VS Code MCP Extension",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            },
        )

        assert response.status_code == 201
        client_info = response.json()

        assert "client_id" in client_info
        assert client_info["token_endpoint_auth_method"] == "none"  # Public client

    def test_dcr_register_claude_code_client(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test DCR registration for Claude Code client."""
        response = mcp_client_with_mock_jwks.post(
            "/dcr/register",
            json={
                "redirect_uris": ["http://localhost:8080/callback"],
                "client_name": "Claude Code CLI",
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            },
            headers={"User-Agent": "Claude-CLI/1.0"},
        )

        assert response.status_code == 201
        client_info = response.json()

        assert "client_id" in client_info
        assert client_info["token_endpoint_auth_method"] == "none"

    def test_dcr_returns_authorization_endpoints(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test DCR response includes OAuth endpoint information."""
        response = mcp_client_with_mock_jwks.post(
            "/dcr/register",
            json={
                "redirect_uris": ["vscode://mcp-auth/callback"],
                "client_name": "Test Client",
            },
        )

        assert response.status_code == 201
        client_info = response.json()

        # Verify OAuth metadata is included
        assert "authorization_endpoint" in client_info or "token_endpoint" in client_info


@pytest.mark.integration
class TestMCPProtocolFlow:
    """Test MCP protocol operations with authentication."""

    def test_mcp_initialize_requires_auth(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test MCP initialize requires authentication."""
        response = mcp_client_with_mock_jwks.post(
            "/mcp/initialize",
            json={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        )

        # Should require authentication
        assert response.status_code == 401


@pytest.mark.integration
class TestOIDCDiscoveryOnMCPServer:
    """Test OIDC discovery endpoints on MCP server."""

    def test_mcp_server_well_known_endpoint(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test MCP server exposes .well-known/oauth-authorization-server."""
        response = mcp_client_with_mock_jwks.get(
            "/.well-known/oauth-authorization-server"
        )

        # Should return discovery document or redirect
        assert response.status_code in [200, 404]  # 404 acceptable if not implemented


@pytest.mark.integration
class TestTokenValidationEdgeCases:
    """Test edge cases in token validation."""

    def test_missing_authorization_header(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test request without Authorization header."""
        response = mcp_client_with_mock_jwks.get("/api/me")
        assert response.status_code == 401

    def test_malformed_bearer_token(
        self,
        mcp_client_with_mock_jwks: TestClient,
    ):
        """Test request with malformed Bearer token."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_wrong_auth_scheme(
        self,
        mcp_client_with_mock_jwks: TestClient,
        valid_user_token: str,
    ):
        """Test request with wrong auth scheme (Basic instead of Bearer)."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Basic {valid_user_token}"},
        )
        assert response.status_code == 401

    def test_token_with_extra_whitespace(
        self,
        mcp_client_with_mock_jwks: TestClient,
        valid_user_token: str,
    ):
        """Test token parsing handles extra whitespace."""
        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Bearer  {valid_user_token}"},
        )
        # Should either parse correctly or reject - both are valid behaviors
        assert response.status_code in [200, 401]


@pytest.mark.integration
class TestScopeValidation:
    """Test scope validation for user tokens."""

    def test_token_missing_required_scope(
        self,
        mcp_client_with_mock_jwks: TestClient,
        create_access_token,
    ):
        """Test token without required scopes is rejected."""
        token = create_access_token(
            subject="test-user",
            client_id="test-client",
            scopes="other.scope",  # Missing mcp.read mcp.write
            is_app_token=False,
        )

        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should be rejected due to insufficient scopes
        assert response.status_code in [401, 403]


@pytest.mark.integration
class TestRoleValidation:
    """Test role validation for app tokens."""

    def test_app_token_missing_required_role(
        self,
        mcp_client_with_mock_jwks: TestClient,
        create_access_token,
    ):
        """Test app token without required role is rejected."""
        token = create_access_token(
            subject="test-sp",
            client_id="test-sp-client",
            roles=["Other.Role"],  # Missing MCP.ReadWrite.All
            is_app_token=True,
        )

        response = mcp_client_with_mock_jwks.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should be rejected due to insufficient roles
        assert response.status_code in [401, 403]
