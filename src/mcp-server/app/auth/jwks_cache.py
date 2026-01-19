"""JWKS (JSON Web Key Set) cache for JWT signature verification."""

import asyncio
from datetime import datetime, timedelta
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
        self._cache: TTLCache = TTLCache(maxsize=1, ttl=self.cache_ttl)
        self._lock = asyncio.Lock()
        self._last_fetch: Optional[datetime] = None

        logger.info(
            "jwks_cache_initialized",
            jwks_url=self.jwks_url,
            cache_ttl_seconds=self.cache_ttl,
        )

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
            self._last_fetch = datetime.utcnow()

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
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                jwks = response.json()

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
        keys = jwks.get("keys", [])

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
            return datetime.utcnow() - self._last_fetch
        return None
