"""User models."""

from pydantic import BaseModel, Field


class User(BaseModel):
    """User account."""

    id: str = Field(..., description="User object ID (oid)")
    username: str = Field(..., description="User principal name (email)")
    name: str = Field(..., description="Display name")
    password: str | None = Field(default=None, description="Password (mock - not validated)")

    class Config:
        """Pydantic config."""

        from_attributes = True
