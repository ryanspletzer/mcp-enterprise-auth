"""Tests for configuration module."""

import os
import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """Test Settings class."""

    def test_settings_from_env(self, test_settings: Settings):
        """Test settings load from environment variables."""
        assert test_settings.ENTRA_TENANT_ID == "test-tenant-id"
        assert test_settings.MCP_SERVER_APP_ID == "api://test-mcp-server"
        assert test_settings.REQUIRED_SCOPE == "test.read test.write"
        assert test_settings.REQUIRED_ROLE == "Test.ReadWrite.All"

    def test_entra_authority_property(self, test_settings: Settings):
        """Test ENTRA_AUTHORITY is constructed correctly."""
        expected = "https://login.microsoftonline.com/test-tenant-id"
        assert test_settings.ENTRA_AUTHORITY == expected

    def test_entra_oidc_config_url_property(self, test_settings: Settings):
        """Test OIDC config URL is constructed correctly."""
        expected = "https://login.microsoftonline.com/test-tenant-id/v2.0/.well-known/openid-configuration"
        assert test_settings.ENTRA_OIDC_CONFIG_URL == expected

    def test_entra_jwks_url_property(self, test_settings: Settings):
        """Test JWKS URL is constructed correctly."""
        expected = "https://login.microsoftonline.com/test-tenant-id/discovery/v2.0/keys"
        assert test_settings.ENTRA_JWKS_URL == expected

    def test_scope_prefix_defaults_to_app_id(self, test_settings: Settings):
        """Test scope prefix defaults to MCP_SERVER_APP_ID."""
        assert test_settings.scope_prefix == test_settings.MCP_SERVER_APP_ID

    def test_get_required_scopes(self, test_settings: Settings):
        """Test get_required_scopes returns list of scopes."""
        scopes = test_settings.get_required_scopes()
        assert isinstance(scopes, list)
        assert "test.read" in scopes
        assert "test.write" in scopes

    def test_get_required_roles(self, test_settings: Settings):
        """Test get_required_roles returns list of roles."""
        roles = test_settings.get_required_roles()
        assert isinstance(roles, list)
        assert "Test.ReadWrite.All" in roles

    def test_get_allowed_token_versions(self, test_settings: Settings):
        """Test get_allowed_token_versions returns list."""
        versions = test_settings.get_allowed_token_versions()
        assert isinstance(versions, list)
        assert "2.0" in versions

    def test_get_cors_origins(self, test_settings: Settings):
        """Test get_cors_origins returns list."""
        origins = test_settings.get_cors_origins()
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_get_cors_methods(self, test_settings: Settings):
        """Test get_cors_methods returns list."""
        methods = test_settings.get_cors_methods()
        assert isinstance(methods, list)
        assert "GET" in methods
        assert "POST" in methods

    def test_validate_scopes_all(self):
        """Test validate_scopes_all returns correct boolean."""
        # With REQUIRED_SCOPES_ALL
        settings = Settings(
            ENTRA_TENANT_ID="test",
            MCP_SERVER_APP_ID="api://test",
            REQUIRED_SCOPE="test.read",
            REQUIRED_SCOPES_ALL="test.read,test.write",
            REQUIRED_ROLE="Test.Role",
            VSCODE_CLIENT_ID="vscode",
            CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
            CLAUDE_CODE_CLIENT_ID="claude-code",
            CHATGPT_CLIENT_ID="chatgpt",
            GENERIC_CLIENT_ID="generic",
        )
        assert settings.validate_scopes_all() is True

        # Without REQUIRED_SCOPES_ALL
        settings2 = Settings(
            ENTRA_TENANT_ID="test",
            MCP_SERVER_APP_ID="api://test",
            REQUIRED_SCOPE="test.read",
            REQUIRED_ROLE="Test.Role",
            VSCODE_CLIENT_ID="vscode",
            CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
            CLAUDE_CODE_CLIENT_ID="claude-code",
            CHATGPT_CLIENT_ID="chatgpt",
            GENERIC_CLIENT_ID="generic",
        )
        assert settings2.validate_scopes_all() is False

    def test_validate_roles_any(self):
        """Test validate_roles_any returns correct boolean."""
        # With REQUIRED_ROLES_ANY
        settings = Settings(
            ENTRA_TENANT_ID="test",
            MCP_SERVER_APP_ID="api://test",
            REQUIRED_SCOPE="test.read",
            REQUIRED_ROLE="Test.Role",
            REQUIRED_ROLES_ANY="Test.Role1,Test.Role2",
            VSCODE_CLIENT_ID="vscode",
            CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
            CLAUDE_CODE_CLIENT_ID="claude-code",
            CHATGPT_CLIENT_ID="chatgpt",
            GENERIC_CLIENT_ID="generic",
        )
        assert settings.validate_roles_any() is True

        # Without REQUIRED_ROLES_ANY
        settings2 = Settings(
            ENTRA_TENANT_ID="test",
            MCP_SERVER_APP_ID="api://test",
            REQUIRED_SCOPE="test.read",
            REQUIRED_ROLE="Test.Role",
            VSCODE_CLIENT_ID="vscode",
            CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
            CLAUDE_CODE_CLIENT_ID="claude-code",
            CHATGPT_CLIENT_ID="chatgpt",
            GENERIC_CLIENT_ID="generic",
        )
        assert settings2.validate_roles_any() is False

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            Settings(
                # Missing ENTRA_TENANT_ID
                MCP_SERVER_APP_ID="api://test",
                REQUIRED_SCOPE="test.read",
                REQUIRED_ROLE="Test.Role",
                VSCODE_CLIENT_ID="vscode",
                CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
                CLAUDE_CODE_CLIENT_ID="claude-code",
                CHATGPT_CLIENT_ID="chatgpt",
                GENERIC_CLIENT_ID="generic",
            )

    def test_default_values(self):
        """Test default values are set correctly."""
        settings = Settings(
            ENTRA_TENANT_ID="test",
            MCP_SERVER_APP_ID="api://test",
            REQUIRED_SCOPE="test.read",
            REQUIRED_ROLE="Test.Role",
            VSCODE_CLIENT_ID="vscode",
            CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
            CLAUDE_CODE_CLIENT_ID="claude-code",
            CHATGPT_CLIENT_ID="chatgpt",
            GENERIC_CLIENT_ID="generic",
        )

        # Check defaults
        assert settings.DEPLOYMENT_MODE == "fargate"
        assert settings.MCP_SERVER_HOST == "0.0.0.0"
        assert settings.MCP_SERVER_PORT == 8000
        assert settings.JWT_CLOCK_SKEW_SECONDS == 300
        assert settings.JWKS_CACHE_TTL_SECONDS == 86400
        assert settings.ENABLE_DCR_ENDPOINT is True
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DEBUG_MODE is False


@pytest.mark.unit
class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_is_cached(self):
        """Test get_settings returns same instance (cached)."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_returns_settings_instance(self):
        """Test get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
