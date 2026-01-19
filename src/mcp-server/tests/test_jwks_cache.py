"""Tests for JWKS cache module."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.auth.jwks_cache import JWKSCache
from app.config import Settings
from app.utils.exceptions import JWKSError


@pytest.mark.unit
@pytest.mark.jwt
class TestJWKSCache:
    """Test JWKSCache class."""

    @pytest.fixture
    def jwks_cache(self, mock_settings: Settings) -> JWKSCache:
        """Create JWKS cache instance."""
        return JWKSCache(mock_settings)

    @pytest.mark.asyncio
    async def test_get_jwks_fetches_on_first_call(self, jwks_cache: JWKSCache, jwks_response):
        """Test JWKS is fetched on first call."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = jwks_response
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await jwks_cache.get_jwks()

            assert result == jwks_response
            assert "keys" in result
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_jwks_returns_cached_on_second_call(self, jwks_cache: JWKSCache, jwks_response):
        """Test JWKS is returned from cache on second call."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = jwks_response
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            # First call
            result1 = await jwks_cache.get_jwks()
            # Second call (should be cached)
            result2 = await jwks_cache.get_jwks()

            assert result1 == result2
            # Should only fetch once
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_jwks_force_refresh(self, jwks_cache: JWKSCache, jwks_response):
        """Test force_refresh bypasses cache."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = jwks_response
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            # First call
            await jwks_cache.get_jwks()
            # Force refresh
            await jwks_cache.get_jwks(force_refresh=True)

            # Should fetch twice
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_jwks_handles_http_error(self, jwks_cache: JWKSCache):
        """Test JWKS fetch handles HTTP errors."""
        with patch.object(jwks_cache, '_fetch_jwks', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = JWKSError(
                "Failed to fetch JWKS: HTTP 500",
                details={"jwks_url": jwks_cache.jwks_url, "status_code": 500}
            )

            with pytest.raises(JWKSError) as exc_info:
                await jwks_cache.get_jwks()

            assert "Failed to fetch JWKS" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_jwks_handles_invalid_structure(self, jwks_cache: JWKSCache):
        """Test JWKS fetch handles invalid structure."""
        with patch.object(jwks_cache, '_fetch_jwks', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = JWKSError(
                "Invalid JWKS structure: missing or invalid 'keys' field",
                details={"jwks_url": jwks_cache.jwks_url}
            )

            with pytest.raises(JWKSError) as exc_info:
                await jwks_cache.get_jwks()

            assert "Invalid JWKS structure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_jwks_handles_empty_keys(self, jwks_cache: JWKSCache):
        """Test JWKS fetch handles empty keys array."""
        with patch.object(jwks_cache, '_fetch_jwks', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = JWKSError(
                "JWKS contains no keys",
                details={"jwks_url": jwks_cache.jwks_url}
            )

            with pytest.raises(JWKSError) as exc_info:
                await jwks_cache.get_jwks()

            assert "JWKS contains no keys" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_key_by_kid_returns_key(self, jwks_cache: JWKSCache, jwks_response):
        """Test get_key_by_kid returns correct key."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = jwks_response
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            key = await jwks_cache.get_key_by_kid("test-key-id-1")

            assert key is not None
            assert key["kid"] == "test-key-id-1"

    @pytest.mark.asyncio
    async def test_get_key_by_kid_returns_none_if_not_found(self, jwks_cache: JWKSCache, jwks_response):
        """Test get_key_by_kid returns None if key not found."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = jwks_response
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client_class.return_value = mock_client

            # Try first call (will fail)
            # Then refresh (will also fail)
            key = await jwks_cache.get_key_by_kid("non-existent-key")

            assert key is None
            # Should try refreshing once
            assert mock_client.get.call_count == 2

    def test_clear_cache(self, jwks_cache: JWKSCache):
        """Test clear_cache clears the cache."""
        # Manually populate cache
        jwks_cache._cache["jwks"] = {"keys": []}

        assert jwks_cache.is_cached is True

        jwks_cache.clear_cache()

        assert jwks_cache.is_cached is False

    def test_is_cached_property(self, jwks_cache: JWKSCache):
        """Test is_cached property."""
        assert jwks_cache.is_cached is False

        # Populate cache
        jwks_cache._cache["jwks"] = {"keys": []}

        assert jwks_cache.is_cached is True

    def test_cache_age_property(self, jwks_cache: JWKSCache):
        """Test cache_age property."""
        from datetime import datetime

        assert jwks_cache.cache_age is None

        # Set last_fetch
        jwks_cache._last_fetch = datetime.utcnow()

        assert jwks_cache.cache_age is not None
        assert jwks_cache.cache_age.total_seconds() >= 0
