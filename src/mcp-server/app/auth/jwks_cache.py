"""JWKS (JSON Web Key Set) cache for JWT signature verification."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from cachetools import TTLCache

from app.config import Settings
from app.utils.exceptions import JWKSError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class JWKSCache:
    """Cache for JWKS (JSON Web Key Set) from Entra ID.

    Fetches and caches public keys used to verify JWT signatures.
    Implements automatic refresh and handles concurrent requests.
    Uses connection pooling for efficient HTTP client usage.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize JWKS cache.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.jwks_url = settings.ENTRA_JWKS_URL
        self.cache_ttl = settings.JWKS_CACHE_TTL_SECONDS

        # TTL cache for JWKS
        self._cache: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=1, ttl=self.cache_ttl)
        self._lock = asyncio.Lock()
        self._last_fetch: Optional[datetime] = None

        # Reusable HTTP client with connection pooling
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            "jwks_cache_initialized",
            jwks_url=self.jwks_url,
            cache_ttl_seconds=self.cache_ttl,
        )

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling.

        Returns:
            Configured async HTTP client
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.settings.JWKS_FETCH_TIMEOUT_SECONDS,
                limits=httpx.Limits(
                    max_keepalive_connections=self.settings.HTTP_MAX_KEEPALIVE_CONNECTIONS,
                    max_connections=self.settings.HTTP_MAX_CONNECTIONS,
                    keepalive_expiry=self.settings.HTTP_KEEPALIVE_EXPIRY_SECONDS,
                ),
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("jwks_http_client_closed")

    async def get_jwks(self, force_refresh: bool = False) -> dict[str, Any]:
        """Get JWKS, fetching from Entra ID if not cached or expired.

        Args:
            force_refresh: Force refresh even if cached

        Returns:
            JWKS dictionary

        Raises:
            JWKSError: If JWKS fetch fails
        """
        # Check cache first (unless force refresh)
        if not force_refresh and "jwks" in self._cache:
            logger.debug("jwks_cache_hit")
            return self._cache["jwks"]

        # Acquire lock to prevent concurrent fetches
        async with self._lock:
            # Double-check cache after acquiring lock
            if not force_refresh and "jwks" in self._cache:
                logger.debug("jwks_cache_hit_after_lock")
                return self._cache["jwks"]

            # Fetch JWKS
            logger.info("jwks_fetching", url=self.jwks_url)
            jwks = await self._fetch_jwks()

            # Cache JWKS
            self._cache["jwks"] = jwks
            self._last_fetch = datetime.now(timezone.utc)

            logger.info(
                "jwks_cached",
                num_keys=len(jwks.get("keys", [])),
                cache_ttl_seconds=self.cache_ttl,
            )

            return jwks

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS from Entra ID.

        Returns:
            JWKS dictionary

        Raises:
            JWKSError: If fetch fails
        """
        try:
            client = self._get_http_client()
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            jwks: dict[str, Any] = response.json()

            # Validate JWKS structure
            if "keys" not in jwks or not isinstance(jwks["keys"], list):
                raise JWKSError(
                    "Invalid JWKS structure: missing or invalid 'keys' field",
                    details={"jwks_url": self.jwks_url},
                )

            if len(jwks["keys"]) == 0:
                raise JWKSError(
                    "JWKS contains no keys",
                    details={"jwks_url": self.jwks_url},
                )

            return jwks

        except httpx.HTTPStatusError as e:
            logger.error(
                "jwks_fetch_http_error",
                status_code=e.response.status_code,
                url=self.jwks_url,
                error=str(e),
            )
            raise JWKSError(
                f"Failed to fetch JWKS: HTTP {e.response.status_code}",
                details={
                    "jwks_url": self.jwks_url,
                    "status_code": e.response.status_code,
                },
            ) from e

        except httpx.RequestError as e:
            logger.error(
                "jwks_fetch_request_error",
                url=self.jwks_url,
                error=str(e),
            )
            raise JWKSError(
                f"Failed to fetch JWKS: {str(e)}",
                details={"jwks_url": self.jwks_url},
            ) from e

        except Exception as e:
            logger.error(
                "jwks_fetch_unexpected_error",
                url=self.jwks_url,
                error=str(e),
            )
            raise JWKSError(
                f"Unexpected error fetching JWKS: {str(e)}",
                details={"jwks_url": self.jwks_url},
            ) from e

    async def get_key_by_kid(self, kid: str) -> Optional[dict[str, Any]]:
        """Get a specific key from JWKS by key ID (kid).

        Args:
            kid: Key ID from JWT header

        Returns:
            Key dictionary or None if not found

        Raises:
            JWKSError: If JWKS fetch fails
        """
        jwks = await self.get_jwks()
        keys: list[dict[str, Any]] = jwks.get("keys", [])

        for key in keys:
            if key.get("kid") == kid:
                logger.debug("jwks_key_found", kid=kid)
                return key

        # Key not found - try refreshing JWKS once
        logger.warning("jwks_key_not_found_refreshing", kid=kid)
        jwks = await self.get_jwks(force_refresh=True)
        keys = jwks.get("keys", [])

        for key in keys:
            if key.get("kid") == kid:
                logger.info("jwks_key_found_after_refresh", kid=kid)
                return key

        logger.error("jwks_key_not_found", kid=kid, num_keys=len(keys))
        return None

    def clear_cache(self) -> None:
        """Clear the JWKS cache."""
        self._cache.clear()
        logger.info("jwks_cache_cleared")

    @property
    def is_cached(self) -> bool:
        """Check if JWKS is currently cached."""
        return "jwks" in self._cache

    @property
    def cache_age(self) -> Optional[timedelta]:
        """Get age of cached JWKS."""
        if self._last_fetch:
            return datetime.now(timezone.utc) - self._last_fetch
        return None
