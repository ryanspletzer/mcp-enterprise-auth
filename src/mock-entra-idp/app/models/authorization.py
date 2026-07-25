"""Authorization code and session models."""

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field


class AuthorizationSession(BaseModel):
    """Authorization session (before login/consent)."""

    session_id: str = Field(..., description="Session identifier")
    client_id: str = Field(..., description="Client ID")
    redirect_uri: str = Field(..., description="Redirect URI")
    scope: str = Field(..., description="Requested scope")
    state: str | None = Field(default=None, description="Client state parameter")
    code_challenge: str | None = Field(default=None, description="PKCE code challenge")
    code_challenge_method: str | None = Field(default=None, description="PKCE challenge method")
    user_id: str | None = Field(default=None, description="Authenticated user ID")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Session creation time"
    )
    expires_at: datetime = Field(..., description="Session expiration time")

    @classmethod
    def create(
        cls,
        session_id: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        ttl: int = 600,
    ) -> "AuthorizationSession":
        """Create new authorization session."""
        now = datetime.now(timezone.utc)
        return cls(
            session_id=session_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    class Config:
        """Pydantic config."""

        from_attributes = True


class AuthorizationCode(BaseModel):
    """Authorization code for OAuth code exchange."""

    code: str = Field(..., description="Authorization code")
    client_id: str = Field(..., description="Client ID")
    user_id: str = Field(..., description="User ID")
    scope: str = Field(..., description="Granted scope")
    redirect_uri: str = Field(..., description="Redirect URI")
    code_challenge: str | None = Field(default=None, description="PKCE code challenge")
    code_challenge_method: str | None = Field(default=None, description="PKCE challenge method")
    audience: str | None = Field(default=None, description="Token audience")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Code creation time"
    )
    expires_at: datetime = Field(..., description="Code expiration time")
    used: bool = Field(default=False, description="Whether code has been used")

    @classmethod
    def create(
        cls,
        code: str,
        client_id: str,
        user_id: str,
        scope: str,
        redirect_uri: str,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        audience: str | None = None,
        ttl: int = 600,
    ) -> "AuthorizationCode":
        """Create new authorization code."""
        now = datetime.now(timezone.utc)
        return cls(
            code=code,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            audience=audience,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )

    def is_expired(self) -> bool:
        """Check if code is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    class Config:
        """Pydantic config."""

        from_attributes = True


class RefreshToken(BaseModel):
    """Refresh token."""

    token: str = Field(..., description="Refresh token value")
    client_id: str = Field(..., description="Client ID")
    user_id: str = Field(..., description="User ID")
    scope: str = Field(..., description="Granted scope")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Token creation time"
    )
    expires_at: datetime = Field(..., description="Token expiration time")
    revoked: bool = Field(default=False, description="Whether token has been revoked")

    @classmethod
    def create(
        cls,
        token: str,
        client_id: str,
        user_id: str,
        scope: str,
        ttl: int = 86400,
    ) -> "RefreshToken":
        """Create new refresh token."""
        now = datetime.now(timezone.utc)
        return cls(
            token=token,
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
        )

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) > self.expires_at

    class Config:
        """Pydantic config."""

        from_attributes = True
