"""Request validation utilities."""

import structlog

logger = structlog.get_logger(__name__)


def validate_redirect_uri(redirect_uri: str, allowed_uris: list[str]) -> bool:
    """
    Validate redirect URI against allowed URIs.

    Args:
        redirect_uri: The redirect URI from request
        allowed_uris: List of allowed redirect URIs for client

    Returns:
        True if valid, False otherwise
    """
    if not redirect_uri:
        logger.warning("redirect_uri_validation_failed", reason="empty_uri")
        return False

    if not allowed_uris:
        logger.warning("redirect_uri_validation_failed", reason="no_allowed_uris")
        return False

    # Exact match required
    valid = redirect_uri in allowed_uris

    if not valid:
        logger.warning(
            "redirect_uri_validation_failed",
            redirect_uri=redirect_uri,
            allowed_uris=allowed_uris,
        )

    return valid


def validate_scope(scope: str) -> bool:
    """
    Validate scope parameter.

    Args:
        scope: Space-separated scope string

    Returns:
        True if valid, False otherwise
    """
    if not scope:
        return False

    # Basic validation - scope should be non-empty
    scopes = scope.split()
    return len(scopes) > 0


def parse_scope(scope: str) -> list[str]:
    """
    Parse scope string into list of individual scopes.

    Args:
        scope: Space-separated scope string

    Returns:
        List of scope strings
    """
    if not scope:
        return []
    return scope.split()
