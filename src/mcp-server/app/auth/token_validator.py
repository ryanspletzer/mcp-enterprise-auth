"""Token type detection and permission validation."""

from enum import Enum
from typing import Any

from app.config import Settings
from app.utils.exceptions import AuthorizationError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TokenType(str, Enum):
    """Token type enumeration."""

    USER = "user"  # Delegated permissions (user context)
    APP_ONLY = "app_only"  # Application permissions (service principal)


class TokenValidator:
    """Validates token permissions based on token type.

    Detects whether token is user (delegated) or app-only (service principal)
    and validates the appropriate permission claims (scp vs roles).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize token validator.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.required_scopes = settings.get_required_scopes()
        self.required_roles = settings.get_required_roles()
        self.validate_scopes_all = settings.validate_scopes_all()
        self.validate_roles_any = settings.validate_roles_any()

        logger.info(
            "token_validator_initialized",
            required_scopes=self.required_scopes,
            required_roles=self.required_roles,
            scopes_all=self.validate_scopes_all,
            roles_any=self.validate_roles_any,
        )

    def detect_token_type(self, claims: dict[str, Any]) -> TokenType:
        """Detect token type from claims.

        Token is app-only if:
        - idtyp claim is "app", OR
        - scp claim is absent

        Otherwise, it's a user token (delegated permissions).

        Args:
            claims: JWT claims

        Returns:
            Token type
        """
        idtyp = claims.get("idtyp")
        scp = claims.get("scp")

        # Check idtyp first (most reliable)
        if idtyp == "app":
            logger.debug("token_type_detected_app_only_by_idtyp", idtyp=idtyp)
            return TokenType.APP_ONLY

        # Check for absence of scp claim (indicates app-only)
        if scp is None:
            # Double-check: app-only tokens should have roles claim
            roles = claims.get("roles")
            if roles:
                logger.debug("token_type_detected_app_only_by_absence_of_scp")
                return TokenType.APP_ONLY

        # Default to user token
        logger.debug("token_type_detected_user", scp=scp)
        return TokenType.USER

    def validate_permissions(
        self, claims: dict[str, Any], token_type: TokenType
    ) -> dict[str, Any]:
        """Validate token permissions based on type.

        Args:
            claims: JWT claims
            token_type: Detected token type

        Returns:
            Permission info dict with validated permissions

        Raises:
            AuthorizationError: If permissions are insufficient
        """
        if token_type == TokenType.USER:
            return self._validate_user_permissions(claims)
        else:
            return self._validate_app_permissions(claims)

    def _validate_user_permissions(self, claims: dict[str, Any]) -> dict[str, Any]:
        """Validate user (delegated) permissions via scp claim.

        Args:
            claims: JWT claims

        Returns:
            Permission info dict

        Raises:
            AuthorizationError: If scopes are insufficient
        """
        scp_claim = claims.get("scp", "")
        scopes = scp_claim.split() if scp_claim else []

        if not scopes:
            logger.warning("user_token_missing_scopes", claims_keys=list(claims.keys()))
            raise AuthorizationError(
                "User token missing scope claim",
                error_code="missing_scope",
                details={"required_scopes": self.required_scopes},
            )

        # Validate scopes
        if self.validate_scopes_all:
            # Require ALL scopes (AND logic)
            missing_scopes = [s for s in self.required_scopes if s not in scopes]
            if missing_scopes:
                logger.warning(
                    "user_token_insufficient_scopes_all",
                    required=self.required_scopes,
                    actual=scopes,
                    missing=missing_scopes,
                )
                raise AuthorizationError(
                    f"Missing required scopes: {', '.join(missing_scopes)}",
                    error_code="insufficient_scope",
                    details={
                        "required_scopes": self.required_scopes,
                        "actual_scopes": scopes,
                        "missing_scopes": missing_scopes,
                    },
                )
        else:
            # Require ANY scope (OR logic)
            has_required_scope = any(s in scopes for s in self.required_scopes)
            if not has_required_scope:
                logger.warning(
                    "user_token_insufficient_scopes_any",
                    required=self.required_scopes,
                    actual=scopes,
                )
                raise AuthorizationError(
                    f"Token must have at least one of: {', '.join(self.required_scopes)}",
                    error_code="insufficient_scope",
                    details={
                        "required_scopes": self.required_scopes,
                        "actual_scopes": scopes,
                    },
                )

        logger.info(
            "user_permissions_validated",
            scopes=scopes,
            user=claims.get("preferred_username") or claims.get("oid"),
        )

        return {
            "token_type": TokenType.USER,
            "scopes": scopes,
            "user_id": claims.get("oid"),
            "user_principal": claims.get("preferred_username"),
            "user_name": claims.get("name"),
            "client_id": claims.get("appid") or claims.get("azp"),
        }

    def _validate_app_permissions(self, claims: dict[str, Any]) -> dict[str, Any]:
        """Validate app-only (application) permissions via roles claim.

        Args:
            claims: JWT claims

        Returns:
            Permission info dict

        Raises:
            AuthorizationError: If roles are insufficient
        """
        roles = claims.get("roles", [])

        if not roles:
            logger.warning("app_token_missing_roles", claims_keys=list(claims.keys()))
            raise AuthorizationError(
                "App-only token missing roles claim",
                error_code="missing_role",
                details={"required_roles": self.required_roles},
            )

        # Validate roles (typically ANY role is sufficient, but configurable)
        if self.validate_roles_any:
            # Require ANY role (OR logic)
            has_required_role = any(r in roles for r in self.required_roles)
            if not has_required_role:
                logger.warning(
                    "app_token_insufficient_roles",
                    required=self.required_roles,
                    actual=roles,
                )
                raise AuthorizationError(
                    f"Token must have at least one of: {', '.join(self.required_roles)}",
                    error_code="insufficient_permissions",
                    details={
                        "required_roles": self.required_roles,
                        "actual_roles": roles,
                    },
                )
        else:
            # Require specific role (exact match)
            if self.required_roles[0] not in roles:
                logger.warning(
                    "app_token_missing_required_role",
                    required=self.required_roles[0],
                    actual=roles,
                )
                raise AuthorizationError(
                    f"Token must have role: {self.required_roles[0]}",
                    error_code="insufficient_permissions",
                    details={
                        "required_role": self.required_roles[0],
                        "actual_roles": roles,
                    },
                )

        logger.info(
            "app_permissions_validated",
            roles=roles,
            app_id=claims.get("appid") or claims.get("azp"),
        )

        return {
            "token_type": TokenType.APP_ONLY,
            "roles": roles,
            "service_principal_id": claims.get("oid"),
            "app_id": claims.get("appid") or claims.get("azp"),
            "app_display_name": claims.get("app_displayname"),
        }

    def extract_identity(self, claims: dict[str, Any], token_type: TokenType) -> dict[str, Any]:
        """Extract identity information from claims.

        Args:
            claims: JWT claims
            token_type: Token type

        Returns:
            Identity information dict
        """
        base_identity = {
            "token_type": token_type.value,
            "subject": claims.get("sub"),
            "tenant_id": claims.get("tid"),
        }

        if token_type == TokenType.USER:
            return {
                **base_identity,
                "user_id": claims.get("oid"),
                "user_principal": claims.get("preferred_username"),
                "user_name": claims.get("name"),
                "user_email": claims.get("email"),
                "client_id": claims.get("appid") or claims.get("azp"),
            }
        else:
            return {
                **base_identity,
                "service_principal_id": claims.get("oid"),
                "app_id": claims.get("appid") or claims.get("azp"),
                "app_display_name": claims.get("app_displayname"),
            }
