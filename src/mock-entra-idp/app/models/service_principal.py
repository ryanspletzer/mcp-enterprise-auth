"""Service principal models."""

from pydantic import BaseModel, Field


class ServicePrincipal(BaseModel):
    """Service principal (application identity)."""

    client_id: str = Field(..., description="Service principal client ID")
    oid: str = Field(..., description="Service principal object ID")
    display_name: str = Field(..., description="Service principal display name")
    roles: list[str] = Field(default_factory=list, description="Application roles")

    class Config:
        """Pydantic config."""
        from_attributes = True
