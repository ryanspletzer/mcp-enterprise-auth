"""Centralized error message templates for consistent formatting.

This module provides a single source of truth for error messages,
ensuring consistency across the codebase and simplifying maintenance.
"""


class ErrorMessages:
    """Centralized error message templates.

    All error messages should be generated through this class
    to ensure consistent formatting and easier maintenance.
    """

    # -------------------------------------------------------------------------
    # Scope/Permission Errors
    # -------------------------------------------------------------------------

    @staticmethod
    def missing_scopes(missing: list[str]) -> str:
        """Format missing scopes error message.

        Args:
            missing: List of missing scope names

        Returns:
            Formatted error message
        """
        scope_list = ", ".join(f"'{s}'" for s in missing)
        return f"Missing required scopes: {scope_list}"

    @staticmethod
    def insufficient_scopes_any(required: list[str]) -> str:
        """Format insufficient scopes error (OR logic).

        Args:
            required: List of required scope names (any one needed)

        Returns:
            Formatted error message
        """
        scope_list = ", ".join(f"'{s}'" for s in required)
        return f"Token must have at least one of these scopes: {scope_list}"

    @staticmethod
    def missing_scope_claim() -> str:
        """Format missing scope claim error.

        Returns:
            Formatted error message
        """
        return "User token missing scope claim"

    @staticmethod
    def invalid_scope_format(scope: str) -> str:
        """Format invalid scope format error.

        Args:
            scope: The invalid scope value

        Returns:
            Formatted error message
        """
        return f"Invalid scope format: '{scope}'"

    # -------------------------------------------------------------------------
    # Role/Permission Errors
    # -------------------------------------------------------------------------

    @staticmethod
    def missing_roles() -> str:
        """Format missing roles claim error.

        Returns:
            Formatted error message
        """
        return "App-only token missing roles claim"

    @staticmethod
    def insufficient_roles_any(required: list[str]) -> str:
        """Format insufficient roles error (OR logic).

        Args:
            required: List of required role names (any one needed)

        Returns:
            Formatted error message
        """
        role_list = ", ".join(f"'{r}'" for r in required)
        return f"Token must have at least one of these roles: {role_list}"

    @staticmethod
    def missing_required_role(role: str) -> str:
        """Format missing specific role error.

        Args:
            role: The required role name

        Returns:
            Formatted error message
        """
        return f"Token must have role: '{role}'"

    @staticmethod
    def invalid_role_format(role: str) -> str:
        """Format invalid role format error.

        Args:
            role: The invalid role value

        Returns:
            Formatted error message
        """
        return f"Invalid role format: '{role}'"

    # -------------------------------------------------------------------------
    # Token/JWT Errors
    # -------------------------------------------------------------------------

    @staticmethod
    def token_expired() -> str:
        """Format token expired error.

        Returns:
            Formatted error message
        """
        return "Token has expired"

    @staticmethod
    def token_not_yet_valid() -> str:
        """Format token not yet valid error.

        Returns:
            Formatted error message
        """
        return "Token not yet valid (nbf)"

    @staticmethod
    def token_issued_in_future() -> str:
        """Format token issued in future error.

        Returns:
            Formatted error message
        """
        return "Token issued in the future (iat)"

    @staticmethod
    def missing_kid_header() -> str:
        """Format missing kid header error.

        Returns:
            Formatted error message
        """
        return "Missing 'kid' (key ID) in JWT header"

    @staticmethod
    def key_not_found(kid: str) -> str:
        """Format key not found error.

        Args:
            kid: The key ID that was not found

        Returns:
            Formatted error message
        """
        return f"Public key not found for kid: '{kid}'"

    @staticmethod
    def missing_claims(claims: list[str]) -> str:
        """Format missing claims error.

        Args:
            claims: List of missing claim names

        Returns:
            Formatted error message
        """
        claim_list = ", ".join(f"'{c}'" for c in claims)
        return f"Missing required claims: {claim_list}"

    @staticmethod
    def invalid_tenant(expected: str, actual: str | None) -> str:
        """Format invalid tenant error.

        Args:
            expected: Expected tenant ID
            actual: Actual tenant ID from token

        Returns:
            Formatted error message
        """
        return f"Token from unexpected tenant (expected: '{expected}', got: '{actual}')"

    @staticmethod
    def missing_tenant() -> str:
        """Format missing tenant error.

        Returns:
            Formatted error message
        """
        return "Missing tenant ID (tid) claim"

    @staticmethod
    def invalid_token_version(expected: list[str], actual: str | None) -> str:
        """Format invalid token version error.

        Args:
            expected: List of expected versions
            actual: Actual version from token

        Returns:
            Formatted error message
        """
        version_list = ", ".join(f"'{v}'" for v in expected)
        return f"Invalid token version: '{actual}' (expected: {version_list})"

    # -------------------------------------------------------------------------
    # JWKS Errors
    # -------------------------------------------------------------------------

    @staticmethod
    def jwks_fetch_failed(status_code: int) -> str:
        """Format JWKS fetch failed error.

        Args:
            status_code: HTTP status code

        Returns:
            Formatted error message
        """
        return f"Failed to fetch JWKS: HTTP {status_code}"

    @staticmethod
    def jwks_invalid_structure() -> str:
        """Format JWKS invalid structure error.

        Returns:
            Formatted error message
        """
        return "Invalid JWKS structure: missing or invalid 'keys' field"

    @staticmethod
    def jwks_no_keys() -> str:
        """Format JWKS no keys error.

        Returns:
            Formatted error message
        """
        return "JWKS contains no keys"

    # -------------------------------------------------------------------------
    # DCR Errors
    # -------------------------------------------------------------------------

    @staticmethod
    def redirect_uri_not_allowed(client_name: str) -> str:
        """Format redirect URI not allowed error.

        Args:
            client_name: Name of the client

        Returns:
            Formatted error message
        """
        return f"Redirect URI not allowed for '{client_name}'"

    @staticmethod
    def unknown_client_type(client_type: str) -> str:
        """Format unknown client type error.

        Args:
            client_type: The unknown client type

        Returns:
            Formatted error message
        """
        return f"Unknown client type: '{client_type}'"
