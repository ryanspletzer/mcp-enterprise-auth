"""Authentication middleware for MCP server."""

from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwks_cache import JWKSCache
from app.auth.jwt_validator import JWTValidator
from app.auth.token_validator import TokenType, TokenValidator
from app.config import Settings, get_settings
from app.utils.exceptions import AuthenticationError, AuthorizationError, TokenExpiredError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


class AuthContext:
    """Authentication context attached to requests."""

    def __init__(
        self,
        claims: dict[str, Any],
        token_type: TokenType,
        permissions: dict[str, Any],
        identity: dict[str, Any],
    ) -> None:
        """Initialize auth context.

        Args:
            claims: JWT claims
            token_type: Token type (user or app-only)
            permissions: Validated permissions
            identity: Extracted identity information
        """
        self.claims = claims
        self.token_type = token_type
        self.permissions = permissions
        self.identity = identity

    @property
    def is_user(self) -> bool:
        """Check if token is a user (delegated) token."""
        return self.token_type == TokenType.USER

    @property
    def is_app_only(self) -> bool:
        """Check if token is app-only (service principal)."""
        return self.token_type == TokenType.APP_ONLY

    @property
    def user_id(self) -> Optional[str]:
        """Get user ID (oid) for user tokens."""
        return self.identity.get("user_id") if self.is_user else None

    @property
    def service_principal_id(self) -> Optional[str]:
        """Get service principal ID for app-only tokens."""
        return self.identity.get("service_principal_id") if self.is_app_only else None

    @property
    def subject(self) -> str:
        """Get subject claim (stable identifier)."""
        return self.identity.get("subject", "")


class AuthMiddleware:
    """Authentication middleware for validating JWT tokens."""

    def __init__(self, settings: Settings) -> None:
        """Initialize authentication middleware.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.jwks_cache = JWKSCache(settings)
        self.jwt_validator = JWTValidator(settings, self.jwks_cache)
        self.token_validator = TokenValidator(settings)

        logger.info("auth_middleware_initialized")

    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> AuthContext:
        """Validate JWT token and create auth context.

        Args:
            request: FastAPI request
            credentials: HTTP Authorization credentials

        Returns:
            AuthContext with validated token information

        Raises:
            HTTPException: If authentication fails
        """
        try:
            # Extract token from Authorization header
            if not credentials:
                # Check if mock auth is enabled (for testing)
                if self.settings.ENABLE_MOCK_AUTH:
                    return self._create_mock_auth_context()

                logger.warning(
                    "auth_missing_credentials",
                    path=request.url.path,
                    client=request.client.host if request.client else None,
                )
                raise AuthenticationError(
                    "Missing Authorization header",
                    error_code="missing_authorization",
                )

            token = credentials.credentials

            logger.debug(
                "auth_validating_token",
                path=request.url.path,
                client=request.client.host if request.client else None,
            )

            # Validate JWT
            claims = await self.jwt_validator.validate_token(token)

            # Detect token type
            token_type = self.token_validator.detect_token_type(claims)

            # Validate permissions
            permissions = self.token_validator.validate_permissions(claims, token_type)

            # Extract identity
            identity = self.token_validator.extract_identity(claims, token_type)

            # Create auth context
            auth_context = AuthContext(
                claims=claims,
                token_type=token_type,
                permissions=permissions,
                identity=identity,
            )

            logger.info(
                "auth_success",
                token_type=token_type.value,
                subject=auth_context.subject,
                path=request.url.path,
            )

            return auth_context

        except TokenExpiredError as e:
            logger.warning("auth_token_expired", error=e.message)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": e.error_code,
                    "error_description": e.message,
                },
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        except AuthenticationError as e:
            logger.warning("auth_failed", error=e.message, details=e.details)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": e.error_code,
                    "error_description": e.message,
                },
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        except AuthorizationError as e:
            logger.warning("auth_insufficient_permissions", error=e.message, details=e.details)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": e.error_code,
                    "error_description": e.message,
                },
            ) from e

        except Exception as e:
            logger.error("auth_unexpected_error", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "server_error",
                    "error_description": "An unexpected error occurred during authentication",
                },
            ) from e

    def _create_mock_auth_context(self) -> AuthContext:
        """Create mock auth context for testing.

        Returns:
            Mock AuthContext

        Warning:
            This should NEVER be enabled in production!
        """
        logger.warning("auth_using_mock_context_do_not_use_in_production")

        mock_claims = {
            "aud": self.settings.MCP_SERVER_APP_ID,
            "iss": f"{self.settings.ENTRA_AUTHORITY}/v2.0",
            "sub": "mock-user-subject",
            "oid": "mock-user-oid",
            "tid": self.settings.ENTRA_TENANT_ID,
            "preferred_username": "mock@example.com",
            "name": "Mock User",
            "scp": "mcp.read mcp.write",
            "ver": "2.0",
        }

        return AuthContext(
            claims=mock_claims,
            token_type=TokenType.USER,
            permissions={
                "token_type": TokenType.USER,
                "scopes": ["mcp.read", "mcp.write"],
                "user_id": "mock-user-oid",
                "user_principal": "mock@example.com",
                "user_name": "Mock User",
            },
            identity={
                "token_type": "user",
                "subject": "mock-user-subject",
                "tenant_id": self.settings.ENTRA_TENANT_ID,
                "user_id": "mock-user-oid",
                "user_principal": "mock@example.com",
                "user_name": "Mock User",
            },
        )


# Dependency for protecting routes
async def get_auth_context(
    request: Request,
    settings: Settings = Depends(get_settings),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthContext:
    """Dependency to get auth context in route handlers.

    Args:
        request: FastAPI request
        settings: Application settings
        credentials: HTTP Authorization credentials

    Returns:
        AuthContext

    Raises:
        HTTPException: If authentication fails
    """
    # Create middleware instance (cached per request)
    if not hasattr(request.state, "auth_middleware"):
        request.state.auth_middleware = AuthMiddleware(settings)

    middleware: AuthMiddleware = request.state.auth_middleware
    return await middleware(request, credentials)


# Dependency for requiring user tokens only
async def require_user_token(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Dependency to require a user (delegated) token.

    Args:
        auth: Auth context from middleware

    Returns:
        AuthContext

    Raises:
        HTTPException: If token is not a user token
    """
    if not auth.is_user:
        logger.warning("auth_user_token_required_but_got_app_token")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "error_description": "This endpoint requires a user token (delegated permissions)",
            },
        )
    return auth


# Dependency for requiring app-only tokens
async def require_app_token(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """Dependency to require an app-only token.

    Args:
        auth: Auth context from middleware

    Returns:
        AuthContext

    Raises:
        HTTPException: If token is not an app-only token
    """
    if not auth.is_app_only:
        logger.warning("auth_app_token_required_but_got_user_token")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "forbidden",
                "error_description": "This endpoint requires an app-only token (application permissions)",
            },
        )
    return auth
