"""Tests for token validator module."""

import pytest

from app.auth.token_validator import TokenType, TokenValidator
from app.config import Settings
from app.utils.exceptions import AuthorizationError


@pytest.mark.unit
@pytest.mark.auth
class TestTokenValidator:
    """Test TokenValidator class."""

    @pytest.fixture
    def token_validator(self, mock_settings: Settings) -> TokenValidator:
        """Create token validator instance."""
        return TokenValidator(mock_settings)

    def test_detect_user_token_by_scp(self, token_validator, user_jwt_claims):
        """Test detect_token_type identifies user token by scp claim."""
        token_type = token_validator.detect_token_type(user_jwt_claims)
        assert token_type == TokenType.USER

    def test_detect_app_token_by_idtyp(self, token_validator, app_only_jwt_claims):
        """Test detect_token_type identifies app token by idtyp."""
        token_type = token_validator.detect_token_type(app_only_jwt_claims)
        assert token_type == TokenType.APP_ONLY

    def test_detect_app_token_by_missing_scp(self, token_validator, app_only_jwt_claims):
        """Test detect_token_type identifies app token by missing scp."""
        claims = app_only_jwt_claims.copy()
        del claims["idtyp"]  # Remove idtyp, rely on missing scp

        token_type = token_validator.detect_token_type(claims)
        assert token_type == TokenType.APP_ONLY

    def test_validate_user_permissions_with_valid_scopes(
        self, token_validator, user_jwt_claims
    ):
        """Test validate_permissions succeeds with valid user scopes."""
        result = token_validator.validate_permissions(user_jwt_claims, TokenType.USER)

        assert result["token_type"] == TokenType.USER
        assert "test.read" in result["scopes"]
        assert "test.write" in result["scopes"]
        assert result["user_id"] == "test-user-oid"
        assert result["user_principal"] == "testuser@example.com"

    def test_validate_user_permissions_with_missing_scope(
        self, token_validator, user_jwt_claims
    ):
        """Test validate_permissions fails with missing scope."""
        claims = user_jwt_claims.copy()
        claims["scp"] = "other.scope"

        with pytest.raises(AuthorizationError) as exc_info:
            token_validator.validate_permissions(claims, TokenType.USER)

        assert "insufficient" in str(exc_info.value).lower()

    def test_validate_user_permissions_with_no_scopes(
        self, token_validator, user_jwt_claims
    ):
        """Test validate_permissions fails when scp claim is missing."""
        claims = user_jwt_claims.copy()
        del claims["scp"]

        with pytest.raises(AuthorizationError) as exc_info:
            token_validator.validate_permissions(claims, TokenType.USER)

        assert "missing scope" in str(exc_info.value).lower()

    def test_validate_app_permissions_with_valid_roles(
        self, token_validator, app_only_jwt_claims
    ):
        """Test validate_permissions succeeds with valid app roles."""
        result = token_validator.validate_permissions(
            app_only_jwt_claims, TokenType.APP_ONLY
        )

        assert result["token_type"] == TokenType.APP_ONLY
        assert "Test.ReadWrite.All" in result["roles"]
        assert result["service_principal_id"] == "test-sp-oid"
        assert result["app_id"] == "test-sp-client-id"

    def test_validate_app_permissions_with_missing_role(
        self, token_validator, app_only_jwt_claims
    ):
        """Test validate_permissions fails with missing role."""
        claims = app_only_jwt_claims.copy()
        claims["roles"] = ["Other.Role"]

        with pytest.raises(AuthorizationError) as exc_info:
            token_validator.validate_permissions(claims, TokenType.APP_ONLY)

        assert "insufficient" in str(exc_info.value).lower()

    def test_validate_app_permissions_with_no_roles(
        self, token_validator, app_only_jwt_claims
    ):
        """Test validate_permissions fails when roles claim is missing."""
        claims = app_only_jwt_claims.copy()
        del claims["roles"]

        with pytest.raises(AuthorizationError) as exc_info:
            token_validator.validate_permissions(claims, TokenType.APP_ONLY)

        assert "missing roles" in str(exc_info.value).lower()

    def test_extract_identity_for_user_token(self, token_validator, user_jwt_claims):
        """Test extract_identity for user token."""
        identity = token_validator.extract_identity(user_jwt_claims, TokenType.USER)

        assert identity["token_type"] == "user"
        assert identity["user_id"] == "test-user-oid"
        assert identity["user_principal"] == "testuser@example.com"
        assert identity["user_name"] == "Test User"
        assert identity["subject"] == "test-user-subject"
        assert identity["tenant_id"] == "test-tenant-id"

    def test_extract_identity_for_app_token(self, token_validator, app_only_jwt_claims):
        """Test extract_identity for app-only token."""
        identity = token_validator.extract_identity(
            app_only_jwt_claims, TokenType.APP_ONLY
        )

        assert identity["token_type"] == "app_only"
        assert identity["service_principal_id"] == "test-sp-oid"
        assert identity["app_id"] == "test-sp-client-id"
        assert identity["app_display_name"] == "Test Service Principal"
        assert identity["subject"] == "test-sp-oid"

    def test_validate_scopes_all_logic(self):
        """Test AND logic for scope validation."""
        validator = TokenValidator(
            Settings(
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
        )

        # Should pass with all scopes
        claims_valid = {
            "scp": "test.read test.write",
            "oid": "user-id",
            "preferred_username": "user@example.com",
        }
        result = validator.validate_permissions(claims_valid, TokenType.USER)
        assert result is not None

        # Should fail with only one scope
        claims_invalid = {
            "scp": "test.read",
            "oid": "user-id",
        }
        with pytest.raises(AuthorizationError):
            validator.validate_permissions(claims_invalid, TokenType.USER)

    def test_validate_scopes_any_logic(self):
        """Test OR logic for scope validation."""
        validator = TokenValidator(
            Settings(
                ENTRA_TENANT_ID="test",
                MCP_SERVER_APP_ID="api://test",
                REQUIRED_SCOPE="test.read",
                REQUIRED_SCOPES_ANY="test.read,test.write",
                REQUIRED_ROLE="Test.Role",
                VSCODE_CLIENT_ID="vscode",
                CLAUDE_DESKTOP_CLIENT_ID="claude-desktop",
                CLAUDE_CODE_CLIENT_ID="claude-code",
                CHATGPT_CLIENT_ID="chatgpt",
                GENERIC_CLIENT_ID="generic",
            )
        )

        # Should pass with one scope
        claims_one = {
            "scp": "test.read",
            "oid": "user-id",
            "preferred_username": "user@example.com",
        }
        result = validator.validate_permissions(claims_one, TokenType.USER)
        assert result is not None

        # Should also pass with other scope
        claims_other = {
            "scp": "test.write",
            "oid": "user-id",
            "preferred_username": "user@example.com",
        }
        result = validator.validate_permissions(claims_other, TokenType.USER)
        assert result is not None

        # Should fail with wrong scope
        claims_wrong = {
            "scp": "other.scope",
            "oid": "user-id",
        }
        with pytest.raises(AuthorizationError):
            validator.validate_permissions(claims_wrong, TokenType.USER)
