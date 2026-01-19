"""OAuth 2.0 token endpoint."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException

from app.config.settings import Settings, get_settings
from app.crypto.jwt_issuer import JWTIssuer, get_jwt_issuer
from app.crypto.key_manager import KeyManager, get_key_manager
from app.storage.base import StorageBackend
from app.storage.memory import get_storage
from app.utils.exceptions import InvalidClient, InvalidGrant, UnsupportedGrantType
from app.utils.pkce import verify_code_challenge

logger = structlog.get_logger(__name__)

router = APIRouter()


async def get_storage_dep(settings: Annotated[Settings, Depends(get_settings)]) -> StorageBackend:
    """Get storage backend dependency."""
    return get_storage(settings)


async def get_jwt_issuer_dep(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JWTIssuer:
    """Get JWT issuer dependency."""
    key_manager = get_key_manager()
    return get_jwt_issuer(settings, key_manager)


@router.post("/oauth2/v2.0/token")
async def token(
    grant_type: str = Form(..., description="Grant type"),
    code: str | None = Form(None, description="Authorization code (for authorization_code grant)"),
    redirect_uri: str | None = Form(None, description="Redirect URI"),
    client_id: str | None = Form(None, description="Client ID"),
    client_secret: str | None = Form(None, description="Client secret"),
    code_verifier: str | None = Form(None, description="PKCE code verifier"),
    refresh_token: str | None = Form(None, description="Refresh token (for refresh_token grant)"),
    scope: str | None = Form(None, description="Requested scope"),
    settings: Settings = Depends(get_settings),
    storage: StorageBackend = Depends(get_storage_dep),
    jwt_issuer: JWTIssuer = Depends(get_jwt_issuer_dep),
) -> dict:
    """
    OAuth 2.0 token endpoint.

    Supports:
    - authorization_code grant (with PKCE)
    - refresh_token grant
    - client_credentials grant
    """
    logger.info("token_request", grant_type=grant_type, client_id=client_id)

    try:
        if grant_type == "authorization_code":
            return await handle_authorization_code_grant(
                code=code,
                redirect_uri=redirect_uri,
                client_id=client_id,
                client_secret=client_secret,
                code_verifier=code_verifier,
                settings=settings,
                storage=storage,
                jwt_issuer=jwt_issuer,
            )
        elif grant_type == "refresh_token":
            return await handle_refresh_token_grant(
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
                settings=settings,
                storage=storage,
                jwt_issuer=jwt_issuer,
            )
        elif grant_type == "client_credentials":
            return await handle_client_credentials_grant(
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
                settings=settings,
                storage=storage,
                jwt_issuer=jwt_issuer,
            )
        else:
            raise UnsupportedGrantType(f"Grant type '{grant_type}' is not supported")

    except (InvalidClient, InvalidGrant, UnsupportedGrantType) as e:
        logger.warning("token_request_failed", error=e.error, description=e.error_description)
        raise HTTPException(
            status_code=400,
            detail={
                "error": e.error,
                "error_description": e.error_description,
            },
        )


async def handle_authorization_code_grant(
    code: str | None,
    redirect_uri: str | None,
    client_id: str | None,
    client_secret: str | None,
    code_verifier: str | None,
    settings: Settings,
    storage: StorageBackend,
    jwt_issuer: JWTIssuer,
) -> dict:
    """Handle authorization_code grant type."""
    # Validate required parameters
    if not code or not redirect_uri or not client_id:
        raise InvalidGrant("Missing required parameters")

    # Validate authorization code
    auth_code = await storage.get_authorization_code(code)
    if not auth_code or auth_code.is_expired() or auth_code.used:
        raise InvalidGrant("Invalid or expired authorization code")

    # Validate client
    client = await storage.get_client(auth_code.client_id)
    if not client or client.client_id != client_id:
        raise InvalidClient("Client mismatch")

    # Validate client secret (for confidential clients)
    if client.client_type == "confidential":
        if not client_secret or client_secret != client.client_secret:
            raise InvalidClient("Invalid client credentials")

    # Validate redirect URI
    if redirect_uri != auth_code.redirect_uri:
        raise InvalidGrant("Redirect URI mismatch")

    # Validate PKCE
    if auth_code.code_challenge:
        if not code_verifier:
            raise InvalidGrant("PKCE code_verifier required")
        if not verify_code_challenge(
            code_verifier,
            auth_code.code_challenge,
            auth_code.code_challenge_method or "S256",
        ):
            raise InvalidGrant("Invalid PKCE code_verifier")

    # Get user
    user = await storage.get_user(auth_code.user_id)
    if not user:
        raise InvalidGrant("User not found")

    # Determine client authentication method
    # 0 = public client, 1 = confidential (secret), 2 = certificate
    client_auth_method = 1 if client.client_type == "confidential" else 0

    # Issue access token
    access_token_data = jwt_issuer.issue_user_token(
        client_id=client_id,
        user_id=user.id,
        scopes=auth_code.scope.split(),
        audience=auth_code.audience or settings.MCP_SERVER_APP_ID,
        username=user.username,
        name=user.name,
        client_auth_method=client_auth_method,
    )

    # Issue refresh token
    refresh_token_value = jwt_issuer.issue_refresh_token(
        client_id=client_id,
        user_id=user.id,
        scope=auth_code.scope,
    )

    # Store refresh token
    await storage.create_refresh_token(
        token=refresh_token_value,
        client_id=client_id,
        user_id=user.id,
        scope=auth_code.scope,
    )

    # Revoke authorization code (single use)
    await storage.revoke_authorization_code(code)

    logger.info(
        "authorization_code_grant_success",
        client_id=client_id,
        user_id=user.id,
    )

    return {
        **access_token_data,
        "refresh_token": refresh_token_value,
    }


async def handle_refresh_token_grant(
    refresh_token: str | None,
    client_id: str | None,
    client_secret: str | None,
    scope: str | None,
    settings: Settings,
    storage: StorageBackend,
    jwt_issuer: JWTIssuer,
) -> dict:
    """Handle refresh_token grant type."""
    # Validate required parameters
    if not refresh_token or not client_id:
        raise InvalidGrant("Missing required parameters")

    # Validate refresh token
    refresh_token_obj = await storage.get_refresh_token(refresh_token)
    if not refresh_token_obj or refresh_token_obj.is_expired() or refresh_token_obj.revoked:
        raise InvalidGrant("Invalid or expired refresh token")

    # Validate client
    client = await storage.get_client(client_id)
    if not client or client.client_id != refresh_token_obj.client_id:
        raise InvalidClient("Client mismatch")

    # Validate client secret (for confidential clients)
    if client.client_type == "confidential":
        if not client_secret or client_secret != client.client_secret:
            raise InvalidClient("Invalid client credentials")

    # Get user
    user = await storage.get_user(refresh_token_obj.user_id)
    if not user:
        raise InvalidGrant("User not found")

    # Use requested scope or fall back to original scope
    token_scope = scope or refresh_token_obj.scope

    # Determine client authentication method
    client_auth_method = 1 if client.client_type == "confidential" else 0

    # Issue new access token
    access_token_data = jwt_issuer.issue_user_token(
        client_id=client_id,
        user_id=user.id,
        scopes=token_scope.split(),
        audience=settings.MCP_SERVER_APP_ID,
        username=user.username,
        name=user.name,
        client_auth_method=client_auth_method,
    )

    # Optionally issue new refresh token (token rotation)
    # For simplicity, we'll reuse the same refresh token
    # In production, you might want to rotate refresh tokens

    logger.info(
        "refresh_token_grant_success",
        client_id=client_id,
        user_id=user.id,
    )

    return {
        **access_token_data,
        "refresh_token": refresh_token,  # Reuse same refresh token
    }


async def handle_client_credentials_grant(
    client_id: str | None,
    client_secret: str | None,
    scope: str | None,
    settings: Settings,
    storage: StorageBackend,
    jwt_issuer: JWTIssuer,
) -> dict:
    """Handle client_credentials grant type."""
    # Validate required parameters
    if not client_id or not client_secret:
        raise InvalidClient("Missing client credentials")

    # Validate client
    client = await storage.get_client(client_id)
    if not client:
        raise InvalidClient("Unknown client")

    # Validate client secret
    if not client.client_secret or client_secret != client.client_secret:
        raise InvalidClient("Invalid client credentials")

    # Validate grant type is allowed
    if "client_credentials" not in client.grant_types:
        raise InvalidClient("Client not authorized for client_credentials grant")

    # Get service principal
    sp = await storage.get_service_principal(client_id)
    if not sp:
        raise InvalidClient("Service principal not found")

    # Parse scope to determine roles
    # Default scope returns all roles
    requested_scope = scope or settings.DEFAULT_SCOPE
    roles = sp.roles  # In production, you'd filter based on requested_scope

    # Client credentials always uses secret (1) or certificate (2)
    # For this mock, we're using secrets, so azpacr = 1
    client_auth_method = 1

    # Issue app-only token
    token_data = jwt_issuer.issue_app_token(
        client_id=client_id,
        app_oid=sp.oid,
        roles=roles,
        audience=settings.MCP_SERVER_APP_ID,
        app_display_name=sp.display_name,
        client_auth_method=client_auth_method,
    )

    logger.info(
        "client_credentials_grant_success",
        client_id=client_id,
        app_oid=sp.oid,
    )

    return token_data
