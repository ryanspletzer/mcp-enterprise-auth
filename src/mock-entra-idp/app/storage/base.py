"""Abstract storage backend interface."""

from abc import ABC, abstractmethod

from app.models.authorization import AuthorizationCode, AuthorizationSession, RefreshToken
from app.models.client import OAuthClient
from app.models.service_principal import ServicePrincipal
from app.models.user import User


class StorageBackend(ABC):
    """Abstract storage backend for OAuth data."""

    # Client Management
    @abstractmethod
    async def get_client(self, client_id: str) -> OAuthClient | None:
        """Get OAuth client by ID."""
        ...

    @abstractmethod
    async def create_client(self, client: OAuthClient) -> None:
        """Create new OAuth client."""
        ...

    # User Management
    @abstractmethod
    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        ...

    @abstractmethod
    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        ...

    @abstractmethod
    async def get_or_create_user(self, username: str) -> User:
        """Get existing user or create new one."""
        ...

    # Service Principal Management
    @abstractmethod
    async def get_service_principal(self, client_id: str) -> ServicePrincipal | None:
        """Get service principal by client ID."""
        ...

    @abstractmethod
    async def create_service_principal(self, sp: ServicePrincipal) -> None:
        """Create new service principal."""
        ...

    # Authorization Session Management
    @abstractmethod
    async def create_auth_session(
        self,
        session_id: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> AuthorizationSession:
        """Create authorization session."""
        ...

    @abstractmethod
    async def get_auth_session(self, session_id: str) -> AuthorizationSession | None:
        """Get authorization session."""
        ...

    @abstractmethod
    async def update_auth_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> None:
        """Update authorization session."""
        ...

    # Authorization Code Management
    @abstractmethod
    async def create_authorization_code(
        self,
        code: str,
        client_id: str,
        user_id: str,
        scope: str,
        redirect_uri: str,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        audience: str | None = None,
    ) -> AuthorizationCode:
        """Create authorization code."""
        ...

    @abstractmethod
    async def get_authorization_code(self, code: str) -> AuthorizationCode | None:
        """Get authorization code."""
        ...

    @abstractmethod
    async def revoke_authorization_code(self, code: str) -> None:
        """Revoke (mark as used) authorization code."""
        ...

    # Refresh Token Management
    @abstractmethod
    async def create_refresh_token(
        self,
        token: str,
        client_id: str,
        user_id: str,
        scope: str,
    ) -> RefreshToken:
        """Create refresh token."""
        ...

    @abstractmethod
    async def get_refresh_token(self, token: str) -> RefreshToken | None:
        """Get refresh token."""
        ...

    @abstractmethod
    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke refresh token."""
        ...
