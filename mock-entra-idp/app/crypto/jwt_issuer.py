"""JWT token issuer with Entra ID-compatible claims."""

import secrets
from datetime import datetime, timedelta
from typing import Any

import structlog
from jose import jwt

from app.config.settings import Settings
from app.crypto.key_manager import KeyManager

logger = structlog.get_logger(__name__)


class JWTIssuer:
    """Issues Entra ID-compatible JWT tokens."""

    def __init__(self, settings: Settings, key_manager: KeyManager):
        """
        Initialize JWT issuer.

        Args:
            settings: Application settings
            key_manager: RSA key manager for signing
        """
        self.settings = settings
        self.key_manager = key_manager
        self.tenant_id = settings.MOCK_TENANT_ID
        self.issuer = settings.issuer

    def issue_user_token(
        self,
        client_id: str,
        user_id: str,
        scopes: list[str],
        audience: str,
        username: str,
        name: str,
        client_auth_method: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Issue user (delegated permissions) access token.

        This token represents a user who has delegated permissions to a client app.
        It includes the 'scp' (scopes) claim and user identity claims.

        Args:
            client_id: Client application ID
            user_id: User's object ID
            scopes: List of delegated scopes
            audience: Token audience (MCP server app ID)
            username: User's UPN/email
            name: User's display name
            client_auth_method: Client authentication method (0=public, 1=secret, 2=cert)
            **kwargs: Additional claims

        Returns:
            Token response dict with access_token, token_type, expires_in, scope
        """
        now = datetime.utcnow()
        exp = now + timedelta(seconds=self.settings.ACCESS_TOKEN_TTL)

        claims = {
            # Standard OIDC claims
            "aud": audience,
            "iss": self.issuer,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            # Entra ID user claims
            "sub": user_id,
            "oid": user_id,
            "tid": self.tenant_id,
            "preferred_username": username,
            "name": name,
            # Delegated permissions
            "scp": " ".join(scopes),
            # Client info
            "appid": client_id,
            "azp": client_id,
            "azpacr": str(client_auth_method),  # V2.0: 0=public, 1=secret, 2=cert
            # Token metadata
            "ver": "2.0",
            "uti": self._generate_uti(),
        }

        # Add any additional claims
        claims.update(kwargs)

        # Sign with current key
        private_key, kid = self.key_manager.get_current_signing_key()
        token = jwt.encode(
            claims,
            private_key,
            algorithm="RS256",
            headers={"typ": "JWT", "alg": "RS256", "kid": kid},
        )

        logger.info(
            "user_token_issued",
            user_id=user_id,
            username=username,
            client_id=client_id,
            scopes=scopes,
            ttl=self.settings.ACCESS_TOKEN_TTL,
        )

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.settings.ACCESS_TOKEN_TTL,
            "scope": " ".join(scopes),
        }

    def issue_app_token(
        self,
        client_id: str,
        app_oid: str,
        roles: list[str],
        audience: str,
        app_display_name: str,
        client_auth_method: int = 1,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Issue app-only (application permissions) access token.

        This token represents a service principal/app acting on its own behalf.
        It includes the 'roles' claim and 'idtyp: app' to indicate app-only token.

        Args:
            client_id: Service principal client ID
            app_oid: Service principal object ID
            roles: List of application roles
            audience: Token audience (MCP server app ID)
            app_display_name: Service principal display name
            client_auth_method: Client authentication method (0=public, 1=secret, 2=cert)
            **kwargs: Additional claims

        Returns:
            Token response dict with access_token, token_type, expires_in
        """
        now = datetime.utcnow()
        exp = now + timedelta(seconds=self.settings.ACCESS_TOKEN_TTL)

        claims = {
            # Standard OIDC claims
            "aud": audience,
            "iss": self.issuer,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            # Entra ID service principal claims
            "sub": app_oid,
            "oid": app_oid,
            "tid": self.tenant_id,
            # Application permissions
            "roles": roles,
            # Client info
            "appid": client_id,
            "azp": client_id,
            "azpacr": str(client_auth_method),  # V2.0: 0=public, 1=secret, 2=cert
            "app_displayname": app_display_name,
            # Token type indicator (critical!)
            "idtyp": "app",
            # Token metadata
            "ver": "2.0",
            "uti": self._generate_uti(),
        }

        # Add any additional claims
        claims.update(kwargs)

        # Sign with current key
        private_key, kid = self.key_manager.get_current_signing_key()
        token = jwt.encode(
            claims,
            private_key,
            algorithm="RS256",
            headers={"typ": "JWT", "alg": "RS256", "kid": kid},
        )

        logger.info(
            "app_token_issued",
            client_id=client_id,
            app_oid=app_oid,
            app_name=app_display_name,
            roles=roles,
            ttl=self.settings.ACCESS_TOKEN_TTL,
        )

        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": self.settings.ACCESS_TOKEN_TTL,
            # Note: No refresh_token for app-only tokens
            # Note: No scope claim for app-only tokens
        }

    def issue_refresh_token(
        self,
        client_id: str,
        user_id: str,
        scope: str,
        **kwargs: Any,
    ) -> str:
        """
        Issue refresh token (opaque string).

        Refresh tokens are opaque strings in Entra ID, not JWTs.

        Args:
            client_id: Client application ID
            user_id: User's object ID
            scope: Requested scope
            **kwargs: Additional metadata

        Returns:
            Opaque refresh token string
        """
        # Generate secure random refresh token
        refresh_token = secrets.token_urlsafe(64)

        logger.info(
            "refresh_token_issued",
            user_id=user_id,
            client_id=client_id,
            scope=scope,
            ttl=self.settings.REFRESH_TOKEN_TTL,
        )

        return refresh_token

    def _generate_uti(self) -> str:
        """
        Generate unique token identifier (uti).

        Returns:
            Random URL-safe string
        """
        return secrets.token_urlsafe(16)


def get_jwt_issuer(settings: Settings, key_manager: KeyManager) -> JWTIssuer:
    """
    Get JWT issuer instance.

    Args:
        settings: Application settings
        key_manager: Key manager for signing

    Returns:
        JWT issuer instance
    """
    return JWTIssuer(settings, key_manager)
