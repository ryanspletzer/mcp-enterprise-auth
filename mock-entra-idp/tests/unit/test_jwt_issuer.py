"""Unit tests for JWTIssuer."""

import pytest
from jose import jwt

from app.config.settings import Settings
from app.crypto.jwt_issuer import JWTIssuer
from app.crypto.key_manager import KeyManager


@pytest.mark.unit
class TestJWTIssuer:
    """Test JWTIssuer functionality."""

    def test_issue_user_token(self, jwt_issuer: JWTIssuer, test_settings: Settings):
        """Test issuing user (delegated) token."""
        token_data = jwt_issuer.issue_user_token(
            client_id="test-client",
            user_id="test-user-oid",
            scopes=["test.read", "test.write"],
            audience="api://test-app",
            username="testuser@example.com",
            name="Test User",
        )

        assert "access_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == test_settings.ACCESS_TOKEN_TTL
        assert token_data["scope"] == "test.read test.write"

        # Decode token (without verification for testing)
        claims = jwt.get_unverified_claims(token_data["access_token"])

        # Verify standard claims
        assert claims["aud"] == "api://test-app"
        assert claims["iss"] == test_settings.issuer
        assert "iat" in claims
        assert "nbf" in claims
        assert "exp" in claims

        # Verify user claims
        assert claims["sub"] == "test-user-oid"
        assert claims["oid"] == "test-user-oid"
        assert claims["tid"] == test_settings.MOCK_TENANT_ID
        assert claims["preferred_username"] == "testuser@example.com"
        assert claims["name"] == "Test User"

        # Verify permissions
        assert claims["scp"] == "test.read test.write"

        # Verify client info
        assert claims["appid"] == "test-client"
        assert claims["azp"] == "test-client"

        # Verify token metadata
        assert claims["ver"] == "2.0"
        assert "uti" in claims

    def test_issue_app_token(self, jwt_issuer: JWTIssuer, test_settings: Settings):
        """Test issuing app-only token."""
        token_data = jwt_issuer.issue_app_token(
            client_id="test-sp-client",
            app_oid="test-sp-oid",
            roles=["Test.ReadWrite.All", "Test.Admin.All"],
            audience="api://test-app",
            app_display_name="Test Service Principal",
        )

        assert "access_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == test_settings.ACCESS_TOKEN_TTL
        # No refresh_token for app-only tokens
        assert "refresh_token" not in token_data
        # No scope for app-only tokens
        assert "scope" not in token_data

        # Decode token
        claims = jwt.get_unverified_claims(token_data["access_token"])

        # Verify app-only specific claims
        assert claims["idtyp"] == "app"  # Critical indicator
        assert claims["roles"] == ["Test.ReadWrite.All", "Test.Admin.All"]
        assert claims["app_displayname"] == "Test Service Principal"

        # Verify no user claims
        assert "scp" not in claims
        assert "preferred_username" not in claims
        assert "name" not in claims

    def test_issue_refresh_token(self, jwt_issuer: JWTIssuer):
        """Test issuing refresh token."""
        refresh_token = jwt_issuer.issue_refresh_token(
            client_id="test-client",
            user_id="test-user-oid",
            scope="test.read",
        )

        # Refresh token is an opaque string
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0

    def test_token_has_kid_header(self, jwt_issuer: JWTIssuer, key_manager: KeyManager):
        """Test that issued tokens have kid in header."""
        token_data = jwt_issuer.issue_user_token(
            client_id="test-client",
            user_id="test-user-oid",
            scopes=["test.read"],
            audience="api://test-app",
            username="test@example.com",
            name="Test",
        )

        # Decode header
        header = jwt.get_unverified_header(token_data["access_token"])

        assert "kid" in header
        assert header["kid"] == key_manager.current_kid
        assert header["alg"] == "RS256"
