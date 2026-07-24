"""Tests for JWT validator module."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.auth.jwks_cache import JWKSCache
from app.auth.jwt_validator import JWTValidator
from app.config import Settings
from app.utils.exceptions import TokenExpiredError, TokenInvalidError


@pytest.mark.unit
@pytest.mark.jwt
@pytest.mark.security
class TestJWTValidator:
    """Test JWTValidator class."""

    @pytest.fixture
    def mock_jwks_cache_instance(self, jwks_response):
        """Create mock JWKS cache."""
        cache = AsyncMock(spec=JWKSCache)
        cache.get_key_by_kid.return_value = jwks_response["keys"][0]
        return cache

    @pytest.fixture
    def jwt_validator(self, mock_settings: Settings, mock_jwks_cache_instance):
        """Create JWT validator instance."""
        return JWTValidator(mock_settings, mock_jwks_cache_instance)

    @pytest.mark.asyncio
    async def test_validate_token_with_valid_user_token(
        self, jwt_validator, valid_user_token, user_jwt_claims, public_key, mock_jwks_cache_instance
    ):
        """Test validate_token with valid user token."""
        # Fix temporal claims to use UTC epoch seconds correctly
        claims = user_jwt_claims.copy()
        now_epoch = int(time.time())
        claims["nbf"] = now_epoch - 60  # 1 minute ago
        claims["iat"] = now_epoch - 60  # 1 minute ago
        claims["exp"] = now_epoch + 3600  # 1 hour from now

        # Mock jwt.decode to return claims (since we can't easily mock crypto validation)
        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.return_value = claims

            result = await jwt_validator.validate_token(valid_user_token)

            assert result == claims
            assert result["scp"] == "test.read test.write"
            mock_jwks_cache_instance.get_key_by_kid.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_with_expired_token(
        self, jwt_validator, expired_token, mock_jwks_cache_instance
    ):
        """Test validate_token with expired token raises TokenExpiredError."""
        from jose.exceptions import ExpiredSignatureError

        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.side_effect = ExpiredSignatureError("Token expired")

            with pytest.raises(TokenExpiredError):
                await jwt_validator.validate_token(expired_token)

    @pytest.mark.asyncio
    async def test_validate_token_without_kid_raises_error(self, jwt_validator, token_without_kid):
        """Test validate_token without kid in header raises error."""
        with pytest.raises(TokenInvalidError) as exc_info:
            await jwt_validator.validate_token(token_without_kid)

        assert "kid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_token_with_unknown_kid(
        self, jwt_validator, valid_user_token, mock_jwks_cache_instance
    ):
        """Test validate_token with unknown kid raises error."""
        mock_jwks_cache_instance.get_key_by_kid.return_value = None

        with pytest.raises(TokenInvalidError) as exc_info:
            await jwt_validator.validate_token(valid_user_token)

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_token_with_wrong_issuer(
        self, jwt_validator, token_wrong_issuer, user_jwt_claims, mock_jwks_cache_instance
    ):
        """Test validate_token with wrong issuer raises error."""
        from jose.exceptions import JWTClaimsError

        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTClaimsError("Invalid issuer")

            with pytest.raises(TokenInvalidError) as exc_info:
                await jwt_validator.validate_token(token_wrong_issuer)

            assert "claims validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_token_with_wrong_audience(
        self, jwt_validator, token_wrong_audience, mock_jwks_cache_instance
    ):
        """Test validate_token with wrong audience raises error."""
        from jose.exceptions import JWTClaimsError

        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTClaimsError("Invalid audience")

            with pytest.raises(TokenInvalidError):
                await jwt_validator.validate_token(token_wrong_audience)

    @pytest.mark.asyncio
    async def test_validate_token_with_wrong_tenant(
        self, jwt_validator, valid_user_token, user_jwt_claims, mock_jwks_cache_instance
    ):
        """Test validate_token with wrong tenant ID raises error."""
        claims = user_jwt_claims.copy()
        claims["tid"] = "wrong-tenant-id"
        # Use time.time() for UTC epoch seconds to avoid timezone issues
        now_epoch = int(time.time())
        claims["nbf"] = now_epoch - 60  # 1 minute ago
        claims["iat"] = now_epoch - 60  # 1 minute ago
        claims["exp"] = now_epoch + 3600  # 1 hour from now

        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.return_value = claims

            with pytest.raises(TokenInvalidError) as exc_info:
                await jwt_validator.validate_token(valid_user_token)

            assert "tenant" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_token_with_missing_required_claims(
        self, jwt_validator, valid_user_token, user_jwt_claims, mock_jwks_cache_instance
    ):
        """Test validate_token with missing required claims raises error."""
        claims = user_jwt_claims.copy()
        del claims["sub"]  # Remove required claim
        # Use time.time() for UTC epoch seconds to avoid timezone issues
        now_epoch = int(time.time())
        claims["nbf"] = now_epoch - 60  # 1 minute ago
        claims["iat"] = now_epoch - 60  # 1 minute ago
        claims["exp"] = now_epoch + 3600  # 1 hour from now

        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.return_value = claims

            with pytest.raises(TokenInvalidError) as exc_info:
                await jwt_validator.validate_token(valid_user_token)

            assert "missing required claims" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_token_with_future_iat(
        self, jwt_validator, valid_user_token, user_jwt_claims, mock_jwks_cache_instance
    ):
        """Test validate_token with iat in future raises error."""
        claims = user_jwt_claims.copy()
        # Use time.time() for UTC epoch seconds to avoid timezone issues
        now_epoch = int(time.time())
        # Set iat far in the future (beyond clock skew tolerance of 5 minutes)
        claims["iat"] = now_epoch + 7200  # 2 hours in the future
        # Set nbf in the past so it passes nbf validation first
        claims["nbf"] = now_epoch - 60  # 1 minute ago
        claims["exp"] = now_epoch + 10800  # 3 hours from now

        with patch("app.auth.jwt_validator.jwt.decode") as mock_decode:
            mock_decode.return_value = claims

            with pytest.raises(TokenInvalidError) as exc_info:
                await jwt_validator.validate_token(valid_user_token)

            assert "future" in str(exc_info.value).lower()

    def test_sanitize_claims_removes_sensitive_data(self, jwt_validator, user_jwt_claims):
        """Test _sanitize_claims removes sensitive claims."""
        claims = user_jwt_claims.copy()
        claims["uti"] = "sensitive-data"
        claims["rh"] = "sensitive-data"
        claims["aio"] = "sensitive-data"

        sanitized = jwt_validator._sanitize_claims(claims)

        assert "uti" not in sanitized
        assert "rh" not in sanitized
        assert "aio" not in sanitized
        assert "oid" in sanitized  # Non-sensitive claims remain
