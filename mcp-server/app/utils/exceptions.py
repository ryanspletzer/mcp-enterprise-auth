"""Custom exceptions for MCP server."""

from typing import Any, Optional


class MCPError(Exception):
    """Base exception for MCP server errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "mcp_error",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize MCP error.

        Args:
            message: Error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(MCPError):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "authentication_failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize authentication error."""
        super().__init__(message, error_code, 401, details)


class AuthorizationError(MCPError):
    """Authorization failed (insufficient permissions)."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str = "insufficient_permissions",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize authorization error."""
        super().__init__(message, error_code, 403, details)


class JWTValidationError(AuthenticationError):
    """JWT validation failed."""

    def __init__(
        self,
        message: str,
        error_code: str = "invalid_token",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize JWT validation error."""
        super().__init__(message, error_code, details)


class TokenExpiredError(JWTValidationError):
    """Token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize token expired error."""
        super().__init__(message, "token_expired", details)


class TokenInvalidError(JWTValidationError):
    """Token is invalid."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize token invalid error."""
        super().__init__(message, "invalid_token", details)


class JWKSError(MCPError):
    """JWKS retrieval or validation failed."""

    def __init__(
        self,
        message: str,
        error_code: str = "jwks_error",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize JWKS error."""
        super().__init__(message, error_code, 500, details)


class DCRError(MCPError):
    """DCR (Dynamic Client Registration) emulation error."""

    def __init__(
        self,
        message: str,
        error_code: str = "dcr_error",
        status_code: int = 400,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize DCR error."""
        super().__init__(message, error_code, status_code, details)
