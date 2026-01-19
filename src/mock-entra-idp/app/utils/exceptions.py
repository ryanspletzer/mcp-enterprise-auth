"""Custom exceptions for OAuth errors."""


class OAuthError(Exception):
    """Base OAuth error."""

    def __init__(self, error: str, error_description: str | None = None):
        """
        Initialize OAuth error.

        Args:
            error: OAuth error code
            error_description: Human-readable error description
        """
        self.error = error
        self.error_description = error_description or error
        super().__init__(self.error_description)


class InvalidRequest(OAuthError):
    """Invalid request error."""

    def __init__(self, description: str | None = None):
        super().__init__("invalid_request", description)


class InvalidClient(OAuthError):
    """Invalid client error."""

    def __init__(self, description: str | None = None):
        super().__init__("invalid_client", description)


class InvalidGrant(OAuthError):
    """Invalid grant error."""

    def __init__(self, description: str | None = None):
        super().__init__("invalid_grant", description)


class UnauthorizedClient(OAuthError):
    """Unauthorized client error."""

    def __init__(self, description: str | None = None):
        super().__init__("unauthorized_client", description)


class UnsupportedGrantType(OAuthError):
    """Unsupported grant type error."""

    def __init__(self, description: str | None = None):
        super().__init__("unsupported_grant_type", description)


class UnsupportedResponseType(OAuthError):
    """Unsupported response type error."""

    def __init__(self, description: str | None = None):
        super().__init__("unsupported_response_type", description)


class AccessDenied(OAuthError):
    """Access denied error."""

    def __init__(self, description: str | None = None):
        super().__init__("access_denied", description)
