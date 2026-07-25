"""OAuth 2.0 authorization endpoint."""

import secrets
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.config.settings import Settings, get_settings
from app.storage.base import StorageBackend
from app.storage.memory import get_storage
from app.utils.exceptions import InvalidClient, InvalidRequest, UnsupportedResponseType
from app.utils.pkce import validate_code_challenge_method
from app.utils.validators import validate_redirect_uri, validate_scope

logger = structlog.get_logger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def get_storage_dep(settings: Annotated[Settings, Depends(get_settings)]) -> StorageBackend:
    """Get storage backend dependency."""
    return get_storage(settings)


@router.get("/oauth2/v2.0/authorize", response_class=HTMLResponse)
async def authorize(
    request: Request,
    client_id: str = Query(..., description="Client identifier"),
    redirect_uri: str = Query(..., description="Redirect URI"),
    response_type: str = Query(..., description="Response type (must be 'code')"),
    scope: str = Query(..., description="Requested scope"),
    state: str | None = Query(None, description="Client state (CSRF protection)"),
    code_challenge: str | None = Query(None, description="PKCE code challenge"),
    code_challenge_method: str | None = Query(None, description="PKCE challenge method"),
    response_mode: str = Query("query", description="Response mode"),
    settings: Settings = Depends(get_settings),
    storage: StorageBackend = Depends(get_storage_dep),
) -> Response:
    """
    OAuth 2.0 authorization endpoint.

    Initiates the authorization code flow with PKCE support.
    """
    logger.info(
        "authorization_request",
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        has_pkce=bool(code_challenge),
    )

    try:
        # Validate client
        client = await storage.get_client(client_id)
        if not client:
            raise InvalidClient("Unknown client")

        # Validate redirect URI
        if not validate_redirect_uri(redirect_uri, client.redirect_uris):
            raise InvalidRequest("Invalid redirect_uri")

        # Validate response type
        if response_type != "code":
            raise UnsupportedResponseType("Only 'code' response type is supported")

        # Validate scope
        if not validate_scope(scope):
            raise InvalidRequest("Invalid scope")

        # Validate PKCE (required for public clients)
        if client.client_type == "public" and client.require_pkce:
            if not code_challenge or not code_challenge_method:
                raise InvalidRequest("PKCE required for public clients")
            if not validate_code_challenge_method(code_challenge_method):
                raise InvalidRequest("Invalid code_challenge_method")

        # Create authorization session
        session_id = secrets.token_urlsafe(32)
        await storage.create_auth_session(
            session_id=session_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        logger.debug(
            "auth_session_created",
            session_id=session_id,
            client_id=client_id,
        )

        # Render login page
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "session_id": session_id,
                "client_name": client.name,
                "scopes": scope.split(),
            },
        )

    except (InvalidClient, InvalidRequest, UnsupportedResponseType) as e:
        logger.warning(
            "authorization_request_failed", error=e.error, description=e.error_description
        )
        # Return error to redirect_uri if possible, otherwise show error page
        if redirect_uri and validate_redirect_uri(
            redirect_uri, client.redirect_uris if client else []
        ):
            error_uri = f"{redirect_uri}?error={e.error}&error_description={e.error_description}"
            if state:
                error_uri += f"&state={state}"
            return RedirectResponse(error_uri, status_code=303)

        raise HTTPException(status_code=400, detail=e.error_description)


@router.post("/oauth2/v2.0/authorize/login", response_class=HTMLResponse)
async def login(
    session_id: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    storage: StorageBackend = Depends(get_storage_dep),
) -> RedirectResponse:
    """
    Handle login form submission.

    Note: Password validation is mocked - any password is accepted.
    """
    logger.info("login_attempt", username=username, session_id=session_id)

    # Get session
    session = await storage.get_auth_session(session_id)
    if not session or session.is_expired():
        raise HTTPException(status_code=400, detail="Invalid or expired session")

    # Authenticate user (mock - always succeeds)
    user = await storage.get_or_create_user(username)

    # Update session with user
    await storage.update_auth_session(session_id, user_id=user.id)

    logger.info("login_success", username=username, user_id=user.id)

    # Redirect to consent
    return RedirectResponse(
        f"/oauth2/v2.0/authorize/consent?session_id={session_id}",
        status_code=303,
    )


@router.get("/oauth2/v2.0/authorize/consent", response_class=HTMLResponse)
async def consent_page(
    request: Request,
    session_id: str = Query(...),
    storage: StorageBackend = Depends(get_storage_dep),
) -> HTMLResponse:
    """Show consent screen."""
    session = await storage.get_auth_session(session_id)
    if not session or not session.user_id or session.is_expired():
        raise HTTPException(status_code=400, detail="Invalid session")

    client = await storage.get_client(session.client_id)
    user = await storage.get_user(session.user_id)

    if not client or not user:
        raise HTTPException(status_code=400, detail="Invalid session data")

    logger.debug(
        "consent_page_shown",
        session_id=session_id,
        client_id=client.client_id,
        user_id=user.id,
    )

    return templates.TemplateResponse(
        "consent.html",
        {
            "request": request,
            "session_id": session_id,
            "client_name": client.name,
            "user_name": user.name,
            "scopes": session.scope.split(),
        },
    )


@router.post("/oauth2/v2.0/authorize/consent", response_class=HTMLResponse)
async def grant_consent(
    session_id: str = Form(...),
    consent: str = Form(...),
    settings: Settings = Depends(get_settings),
    storage: StorageBackend = Depends(get_storage_dep),
) -> RedirectResponse:
    """Handle consent form submission."""
    session = await storage.get_auth_session(session_id)
    if not session or not session.user_id or session.is_expired():
        raise HTTPException(status_code=400, detail="Invalid session")

    logger.info(
        "consent_decision",
        session_id=session_id,
        consent=consent,
    )

    # Check if user denied
    if consent != "approve":
        logger.info("consent_denied", session_id=session_id)
        redirect_uri = session.redirect_uri
        redirect_uri += "?error=access_denied&error_description=User denied consent"
        if session.state:
            redirect_uri += f"&state={session.state}"
        return RedirectResponse(redirect_uri, status_code=303)

    # Generate authorization code
    code = secrets.token_urlsafe(32)
    await storage.create_authorization_code(
        code=code,
        client_id=session.client_id,
        user_id=session.user_id,
        scope=session.scope,
        redirect_uri=session.redirect_uri,
        code_challenge=session.code_challenge,
        code_challenge_method=session.code_challenge_method,
        audience=settings.MCP_SERVER_APP_ID,
    )

    logger.info(
        "authorization_code_issued",
        client_id=session.client_id,
        user_id=session.user_id,
    )

    # Build redirect URI with code
    redirect_uri = session.redirect_uri
    redirect_uri += f"?code={code}"
    if session.state:
        redirect_uri += f"&state={session.state}"

    return RedirectResponse(redirect_uri, status_code=303)
