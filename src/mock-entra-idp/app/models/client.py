"""OAuth client models."""

from typing import Literal

from pydantic import BaseModel, Field


class OAuthClient(BaseModel):
    """OAuth 2.0 client application."""

    client_id: str = Field(..., description="Client identifier")
    client_secret: str | None = Field(
        default=None, description="Client secret (confidential clients only)"
    )
    client_type: Literal["public", "confidential"] = Field(..., description="Client type")
    name: str = Field(..., description="Client display name")
    redirect_uris: list[str] = Field(default_factory=list, description="Authorized redirect URIs")
    grant_types: list[str] = Field(
        default_factory=lambda: ["authorization_code", "refresh_token"],
        description="Allowed grant types",
    )
    response_types: list[str] = Field(
        default_factory=lambda: ["code"],
        description="Allowed response types",
    )
    require_pkce: bool = Field(default=True, description="Require PKCE for auth code flow")

    class Config:
        """Pydantic config."""

        from_attributes = True
