"""OIDC discovery and JWKS endpoints."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.crypto.key_manager import KeyManager, get_key_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/discovery/v2.0/keys")
async def jwks(
    key_manager: Annotated[KeyManager, Depends(get_key_manager)],
) -> dict:
    """
    JWKS (JSON Web Key Set) endpoint.

    Returns public keys for JWT signature verification.
    """
    jwks_data = key_manager.get_jwks()

    logger.debug(
        "jwks_served",
        key_count=len(jwks_data.get("keys", [])),
    )

    return jwks_data


def _get_authorization_server_metadata(settings: Settings) -> dict:
    """
    Generate OAuth 2.0 Authorization Server Metadata per RFC 8414.

    This metadata is shared between OIDC discovery and OAuth AS metadata endpoints.
    """
    return {
        "issuer": settings.issuer,
        "authorization_endpoint": settings.authorization_endpoint,
        "token_endpoint": settings.token_endpoint,
        "jwks_uri": settings.jwks_uri,
        "response_types_supported": ["code"],
        "response_modes_supported": ["query", "fragment", "form_post"],
        "grant_types_supported": [
            "authorization_code",
            "refresh_token",
            "client_credentials",
        ],
        "subject_types_supported": ["pairwise"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "none",
        ],
        "code_challenge_methods_supported": ["plain", "S256"],
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "offline_access",
        ],
        # RFC 8414 additional metadata
        "registration_endpoint": None,  # Not supported (using DCR emulation at MCP server)
        "service_documentation": None,
        "ui_locales_supported": ["en-US"],
    }


@router.get("/.well-known/openid-configuration")
async def openid_configuration(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """
    OIDC discovery endpoint (RFC 8414).

    Returns OpenID Connect discovery metadata.
    This is the primary discovery endpoint for OpenID Connect flows.
    """
    discovery_data = _get_authorization_server_metadata(settings)

    logger.debug("openid_configuration_served")

    return discovery_data


@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """
    OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414).

    Returns authorization server metadata for OAuth 2.0 clients.
    This is an alternative to the OIDC discovery endpoint, providing
    the same metadata in a format specific to OAuth 2.0.
    """
    metadata = _get_authorization_server_metadata(settings)

    logger.debug("oauth_authorization_server_metadata_served")

    return metadata


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mock-entra-idp",
    }
