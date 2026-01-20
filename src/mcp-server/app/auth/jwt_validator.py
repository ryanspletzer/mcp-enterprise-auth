"""JWT validation with comprehensive security checks."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from app.auth.jwks_cache import JWKSCache
from app.config import Settings
from app.utils.exceptions import JWKSError, TokenExpiredError, TokenInvalidError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class JWTValidator:
    """Validates JWTs with comprehensive security checks.

    Performs 8-layer validation:
    1. Structure & format
    2. Signature verification
    3. Temporal validation (exp, nbf, iat)
    4. Required claims validation
    5. Issuer validation
    6. Audience validation
    7. Tenant validation
    8. Token version validation
    """

    def __init__(self, settings: Settings, jwks_cache: JWKSCache) -> None:
        """Initialize JWT validator.

        Args:
            settings: Application settings
            jwks_cache: JWKS cache instance
        """
        self.settings = settings
        self.jwks_cache = jwks_cache

        # Expected values
        self.expected_audience = settings.MCP_SERVER_APP_ID
        self.expected_issuer = f"{settings.ENTRA_AUTHORITY}/v2.0"
        self.expected_tenant_id = settings.ENTRA_TENANT_ID
        self.allowed_versions = settings.get_allowed_token_versions()
        self.clock_skew = settings.JWT_CLOCK_SKEW_SECONDS

        logger.info(
            "jwt_validator_initialized",
            expected_audience=self.expected_audience,
            expected_issuer=self.expected_issuer,
            expected_tenant=self.expected_tenant_id,
            clock_skew_seconds=self.clock_skew,
        )

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token with comprehensive security checks.

        Args:
            token: JWT token string

        Returns:
            Decoded and validated JWT claims

        Raises:
            TokenExpiredError: If token has expired
            TokenInvalidError: If token is invalid
            JWKSError: If JWKS operations fail
        """
        try:
            # Step 1: Decode header without validation to get kid
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise TokenInvalidError(
                    "Missing 'kid' (key ID) in JWT header",
                    details={"header": unverified_header},
                )

            logger.debug("jwt_validation_started", kid=kid)

            # Step 2: Get public key from JWKS
            key_data = await self.jwks_cache.get_key_by_kid(kid)
            if not key_data:
                raise TokenInvalidError(
                    f"Public key not found for kid: {kid}",
                    details={"kid": kid},
                )

            # Step 3: Verify signature and decode claims
            try:
                claims = jwt.decode(
                    token,
                    key_data,
                    algorithms=["RS256"],
                    audience=self.expected_audience,
                    issuer=self.expected_issuer,
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_nbf": True,
                        "verify_iat": True,
                        "verify_aud": True,
                        "verify_iss": True,
                        "require_exp": True,
                        "require_iat": True,
                        "leeway": self.clock_skew,
                    },
                )
            except ExpiredSignatureError as e:
                logger.warning("jwt_expired", kid=kid, error=str(e))
                raise TokenExpiredError(details={"kid": kid}) from e

            except JWTClaimsError as e:
                logger.warning("jwt_claims_error", kid=kid, error=str(e))
                raise TokenInvalidError(
                    f"JWT claims validation failed: {str(e)}",
                    details={"kid": kid},
                ) from e

            except JWTError as e:
                logger.warning("jwt_validation_error", kid=kid, error=str(e))
                raise TokenInvalidError(
                    f"JWT validation failed: {str(e)}",
                    details={"kid": kid},
                ) from e

            # Step 4: Additional validation
            self._validate_temporal_claims(claims)
            self._validate_required_claims(claims)
            self._validate_tenant(claims)
            self._validate_token_version(claims)

            # Log JWT claims if enabled (DEBUG only)
            if self.settings.LOG_JWT_CLAIMS:
                logger.debug("jwt_claims_validated", claims=self._sanitize_claims(claims))
            else:
                logger.info(
                    "jwt_validated",
                    sub=claims.get("sub"),
                    oid=claims.get("oid"),
                    appid=claims.get("appid"),
                    exp=claims.get("exp"),
                )

            return claims

        except (TokenExpiredError, TokenInvalidError, JWKSError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            logger.error("jwt_validation_unexpected_error", error=str(e), exc_info=True)
            raise TokenInvalidError(
                f"Unexpected error during JWT validation: {str(e)}"
            ) from e

    def _validate_temporal_claims(self, claims: dict[str, Any]) -> None:
        """Validate temporal claims (exp, nbf, iat).

        Args:
            claims: JWT claims

        Raises:
            TokenInvalidError: If temporal validation fails
        """
        now = datetime.now(timezone.utc)
        leeway = timedelta(seconds=self.clock_skew)

        # Validate exp (already done by jose, but double-check)
        exp = claims.get("exp")
        if exp:
            exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            if exp_time + leeway < now:
                raise TokenInvalidError(
                    "Token has expired",
                    details={"exp": exp, "now": now.timestamp()},
                )

        # Validate nbf (not before)
        nbf = claims.get("nbf")
        if nbf:
            nbf_time = datetime.fromtimestamp(nbf, tz=timezone.utc)
            if nbf_time - leeway > now:
                raise TokenInvalidError(
                    "Token not yet valid (nbf)",
                    details={"nbf": nbf, "now": now.timestamp()},
                )

        # Validate iat (issued at) - ensure not too old and not in future
        iat = claims.get("iat")
        if iat:
            iat_time = datetime.fromtimestamp(iat, tz=timezone.utc)
            # Token should not be issued in the future
            if iat_time - leeway > now:
                raise TokenInvalidError(
                    "Token issued in the future (iat)",
                    details={"iat": iat, "now": now.timestamp()},
                )

        logger.debug(
            "jwt_temporal_validation_passed",
            exp=exp,
            nbf=nbf,
            iat=iat,
        )

    def _validate_required_claims(self, claims: dict[str, Any]) -> None:
        """Validate required claims are present.

        Args:
            claims: JWT claims

        Raises:
            TokenInvalidError: If required claims are missing
        """
        required_claims = ["iss", "aud", "exp", "iat", "sub", "tid"]

        missing_claims = [claim for claim in required_claims if claim not in claims]

        if missing_claims:
            raise TokenInvalidError(
                f"Missing required claims: {', '.join(missing_claims)}",
                details={"missing_claims": missing_claims},
            )

        logger.debug("jwt_required_claims_present")

    def _validate_tenant(self, claims: dict[str, Any]) -> None:
        """Validate tenant ID matches expected tenant.

        Args:
            claims: JWT claims

        Raises:
            TokenInvalidError: If tenant validation fails
        """
        tid = claims.get("tid")

        if tid != self.expected_tenant_id:
            logger.warning(
                "jwt_invalid_tenant",
                expected=self.expected_tenant_id,
                actual=tid,
            )
            raise TokenInvalidError(
                "Token from unexpected tenant",
                details={
                    "expected_tenant": self.expected_tenant_id,
                    "actual_tenant": tid,
                },
            )

        logger.debug("jwt_tenant_validated", tid=tid)

    def _validate_token_version(self, claims: dict[str, Any]) -> None:
        """Validate token version.

        Args:
            claims: JWT claims

        Raises:
            TokenInvalidError: If token version is invalid
        """
        if not self.settings.VALIDATE_TOKEN_VERSION:
            return

        ver = claims.get("ver")

        if ver not in self.allowed_versions:
            logger.warning(
                "jwt_invalid_version",
                expected=self.allowed_versions,
                actual=ver,
            )
            raise TokenInvalidError(
                f"Invalid token version: {ver}",
                details={
                    "expected_versions": self.allowed_versions,
                    "actual_version": ver,
                },
            )

        logger.debug("jwt_version_validated", ver=ver)

    def _sanitize_claims(self, claims: dict[str, Any]) -> dict[str, Any]:
        """Sanitize claims for logging (remove sensitive data).

        Args:
            claims: JWT claims

        Returns:
            Sanitized claims
        """
        # Create a copy
        sanitized = claims.copy()

        # Remove potentially sensitive claims
        sensitive_claims = ["uti", "rh", "aio"]
        for claim in sensitive_claims:
            sanitized.pop(claim, None)

        return sanitized
