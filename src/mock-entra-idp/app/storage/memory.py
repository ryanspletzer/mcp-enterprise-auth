"""In-memory storage backend."""

import secrets

import structlog

from app.config.settings import Settings
from app.models.authorization import AuthorizationCode, AuthorizationSession, RefreshToken
from app.models.client import OAuthClient
from app.models.service_principal import ServicePrincipal
from app.models.user import User
from app.storage.base import StorageBackend

logger = structlog.get_logger(__name__)


class InMemoryStorage(StorageBackend):
    """In-memory storage implementation."""

    def __init__(self, settings: Settings):
        """Initialize in-memory storage with pre-seeded data."""
        self.settings = settings

        # Storage dictionaries
        self.clients: dict[str, OAuthClient] = {}
        self.users: dict[str, User] = {}
        self.users_by_username: dict[str, User] = {}
        self.service_principals: dict[str, ServicePrincipal] = {}
        self.auth_sessions: dict[str, AuthorizationSession] = {}
        self.auth_codes: dict[str, AuthorizationCode] = {}
        self.refresh_tokens: dict[str, RefreshToken] = {}

        # Seed initial data
        self._seed_clients()
        self._seed_users()
        self._seed_service_principals()

        logger.info(
            "in_memory_storage_initialized",
            clients=len(self.clients),
            users=len(self.users),
            service_principals=len(self.service_principals),
        )

    def _seed_clients(self) -> None:
        """Seed pre-registered OAuth clients."""
        # VS Code Extension (public client)
        vscode_client = OAuthClient(
            client_id=self.settings.VSCODE_CLIENT_ID,
            client_type="public",
            name="VS Code Extension",
            redirect_uris=["http://localhost:8080/callback", "vscode://callback"],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            require_pkce=True,
        )
        self.clients[vscode_client.client_id] = vscode_client

        # Claude Code CLI (public client)
        claude_client = OAuthClient(
            client_id=self.settings.CLAUDE_CODE_CLIENT_ID,
            client_type="public",
            name="Claude Code CLI",
            redirect_uris=["http://localhost:8080/callback", "http://127.0.0.1:8080/callback"],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            require_pkce=True,
        )
        self.clients[claude_client.client_id] = claude_client

        # Confidential Client (backend app)
        confidential_client = OAuthClient(
            client_id=self.settings.CONFIDENTIAL_CLIENT_ID,
            client_secret=self.settings.CONFIDENTIAL_CLIENT_SECRET,
            client_type="confidential",
            name="Backend Application",
            redirect_uris=["http://localhost:8080/callback", "http://localhost:3000/callback"],
            grant_types=["authorization_code", "refresh_token", "client_credentials"],
            response_types=["code"],
            require_pkce=True,  # Defense-in-depth
        )
        self.clients[confidential_client.client_id] = confidential_client

        # Service Principal (app-only)
        sp_client = OAuthClient(
            client_id=self.settings.SERVICE_PRINCIPAL_CLIENT_ID,
            client_secret=self.settings.SERVICE_PRINCIPAL_CLIENT_SECRET,
            client_type="confidential",
            name="Service Principal App",
            redirect_uris=[],  # No redirect for client_credentials
            grant_types=["client_credentials"],
            response_types=[],
            require_pkce=False,  # PKCE not used in client_credentials
        )
        self.clients[sp_client.client_id] = sp_client

        logger.debug("seeded_oauth_clients", count=len(self.clients))

    def _seed_users(self) -> None:
        """Seed pre-registered test users."""
        test_users = self.settings.get_test_users()

        for username in test_users:
            user_id = secrets.token_urlsafe(16)
            display_name = username.split("@")[0].title()

            user = User(
                id=user_id,
                username=username,
                name=display_name,
                password="password123",  # Mock - not validated
            )

            self.users[user_id] = user
            self.users_by_username[username] = user

        logger.debug("seeded_test_users", count=len(self.users))

    def _seed_service_principals(self) -> None:
        """Seed service principals."""
        # Create service principal for the SP client
        sp = ServicePrincipal(
            client_id=self.settings.SERVICE_PRINCIPAL_CLIENT_ID,
            oid=secrets.token_urlsafe(16),
            display_name="Service Principal App",
            roles=["MCP.Read.All", "MCP.ReadWrite.All"],
        )
        self.service_principals[sp.client_id] = sp

        # Create service principal for confidential client (can also use app-only)
        confidential_sp = ServicePrincipal(
            client_id=self.settings.CONFIDENTIAL_CLIENT_ID,
            oid=secrets.token_urlsafe(16),
            display_name="Backend Application",
            roles=["MCP.ReadWrite.All"],
        )
        self.service_principals[confidential_sp.client_id] = confidential_sp

        logger.debug("seeded_service_principals", count=len(self.service_principals))

    # Client Management
    async def get_client(self, client_id: str) -> OAuthClient | None:
        """Get OAuth client by ID."""
        return self.clients.get(client_id)

    async def create_client(self, client: OAuthClient) -> None:
        """Create new OAuth client."""
        self.clients[client.client_id] = client
        logger.info("client_created", client_id=client.client_id, client_name=client.name)

    # User Management
    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self.users.get(user_id)

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return self.users_by_username.get(username)

    async def get_or_create_user(self, username: str) -> User:
        """Get existing user or create new one."""
        user = await self.get_user_by_username(username)
        if user:
            return user

        # Create new user
        user_id = secrets.token_urlsafe(16)
        display_name = username.split("@")[0].title()

        user = User(
            id=user_id,
            username=username,
            name=display_name,
            password="password123",
        )

        self.users[user_id] = user
        self.users_by_username[username] = user

        logger.info("user_created", user_id=user_id, username=username)
        return user

    # Service Principal Management
    async def get_service_principal(self, client_id: str) -> ServicePrincipal | None:
        """Get service principal by client ID."""
        return self.service_principals.get(client_id)

    async def create_service_principal(self, sp: ServicePrincipal) -> None:
        """Create new service principal."""
        self.service_principals[sp.client_id] = sp
        logger.info("service_principal_created", client_id=sp.client_id, name=sp.display_name)

    # Authorization Session Management
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
        session = AuthorizationSession.create(
            session_id=session_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            ttl=self.settings.AUTH_CODE_TTL,
        )
        self.auth_sessions[session_id] = session
        logger.debug("auth_session_created", session_id=session_id, client_id=client_id)
        return session

    async def get_auth_session(self, session_id: str) -> AuthorizationSession | None:
        """Get authorization session."""
        session = self.auth_sessions.get(session_id)
        if session and session.is_expired():
            # Clean up expired session
            del self.auth_sessions[session_id]
            return None
        return session

    async def update_auth_session(self, session_id: str, user_id: str | None = None) -> None:
        """Update authorization session."""
        session = self.auth_sessions.get(session_id)
        if session:
            if user_id is not None:
                session.user_id = user_id
            logger.debug("auth_session_updated", session_id=session_id, user_id=user_id)

    # Authorization Code Management
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
        auth_code = AuthorizationCode.create(
            code=code,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            audience=audience,
            ttl=self.settings.AUTH_CODE_TTL,
        )
        self.auth_codes[code] = auth_code
        logger.debug("authorization_code_created", client_id=client_id, user_id=user_id)
        return auth_code

    async def get_authorization_code(self, code: str) -> AuthorizationCode | None:
        """Get authorization code."""
        auth_code = self.auth_codes.get(code)
        if auth_code and (auth_code.is_expired() or auth_code.used):
            # Clean up expired or used code
            del self.auth_codes[code]
            return None
        return auth_code

    async def revoke_authorization_code(self, code: str) -> None:
        """Revoke (mark as used) authorization code."""
        auth_code = self.auth_codes.get(code)
        if auth_code:
            auth_code.used = True
            logger.debug("authorization_code_revoked", code=code[:8] + "...")

    # Refresh Token Management
    async def create_refresh_token(
        self,
        token: str,
        client_id: str,
        user_id: str,
        scope: str,
    ) -> RefreshToken:
        """Create refresh token."""
        refresh_token = RefreshToken.create(
            token=token,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            ttl=self.settings.REFRESH_TOKEN_TTL,
        )
        self.refresh_tokens[token] = refresh_token
        logger.debug("refresh_token_created", client_id=client_id, user_id=user_id)
        return refresh_token

    async def get_refresh_token(self, token: str) -> RefreshToken | None:
        """Get refresh token."""
        refresh_token = self.refresh_tokens.get(token)
        if refresh_token and (refresh_token.is_expired() or refresh_token.revoked):
            # Clean up expired or revoked token
            del self.refresh_tokens[token]
            return None
        return refresh_token

    async def revoke_refresh_token(self, token: str) -> None:
        """Revoke refresh token."""
        refresh_token = self.refresh_tokens.get(token)
        if refresh_token:
            refresh_token.revoked = True
            logger.debug("refresh_token_revoked", token=token[:8] + "...")


# Global storage instance
_storage: InMemoryStorage | None = None


def get_storage(settings: Settings) -> InMemoryStorage:
    """Get global storage instance."""
    global _storage
    if _storage is None:
        _storage = InMemoryStorage(settings)
    return _storage
