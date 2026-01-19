"""DCR (Dynamic Client Registration) emulation endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.dcr.client_detector import ClientDetector
from app.dcr.client_registry import ClientRegistry
from app.utils.exceptions import DCRError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/dcr", tags=["DCR Emulation"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


class DCRRequest(BaseModel):
    """DCR (Dynamic Client Registration) request.

    Based on RFC 7591 OAuth 2.0 Dynamic Client Registration Protocol.
    """

    redirect_uris: list[str] = Field(..., min_length=1, description="Redirect URIs")
    client_name: Optional[str] = Field(None, description="Client name")
    client_uri: Optional[str] = Field(None, description="Client URI")
    logo_uri: Optional[str] = Field(None, description="Logo URI")
    scope: Optional[str] = Field(None, description="Requested scope")
    contacts: Optional[list[str]] = Field(None, description="Contact emails")
    grant_types: Optional[list[str]] = Field(
        default=["authorization_code"], description="Grant types"
    )
    response_types: Optional[list[str]] = Field(default=["code"], description="Response types")


class DCRResponse(BaseModel):
    """DCR response with client credentials and OAuth endpoints."""

    client_id: str
    client_name: str
    client_type: str
    authorization_endpoint: str
    token_endpoint: str
    end_session_endpoint: str
    issuer: str
    jwks_uri: str
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    token_endpoint_auth_method: str
    scope: str
    tenant_id: str
    require_pkce: bool
    requested_redirect_uri: Optional[str] = None


@router.post(
    "/register",
    response_model=DCRResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Emulated Dynamic Client Registration",
    description="""
    Emulates DCR (Dynamic Client Registration) for MCP clients.

    Since Entra ID doesn't support native DCR, this endpoint detects the client type
    based on redirect_uri, User-Agent, and other context, then returns the appropriate
    pre-registered client credentials from Entra ID.

    Detection priority:
    1. Redirect URI (most reliable)
    2. User-Agent header
    3. Client name from request body
    4. Fallback to generic client
    """,
)
async def register_client(
    request: Request,
    dcr_request: DCRRequest,
    settings: Settings = Depends(get_settings),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
) -> dict[str, Any]:
    """Register a new OAuth client (emulated).

    Args:
        request: FastAPI request
        dcr_request: DCR registration request
        settings: Application settings
        user_agent: User-Agent header

    Returns:
        DCR response with client credentials

    Raises:
        HTTPException: If DCR fails
    """
    # Check if DCR is enabled
    if not settings.ENABLE_DCR_ENDPOINT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DCR endpoint is disabled",
        )

    try:
        # Rate limiting (configured in settings)
        # This is handled by middleware, but we log it
        client_ip = get_remote_address(request)
        logger.info(
            "dcr_request_received",
            client_ip=client_ip,
            redirect_uris=dcr_request.redirect_uris,
            client_name=dcr_request.client_name,
            user_agent=user_agent,
        )

        # Detect client type
        detector = ClientDetector()
        client_type, confidence = detector.get_confidence_score(
            redirect_uri=dcr_request.redirect_uris[0] if dcr_request.redirect_uris else None,
            user_agent=user_agent,
            client_name=dcr_request.client_name,
        )

        logger.info(
            "client_type_detected",
            client_type=client_type.value,
            confidence=confidence,
        )

        # Validate redirect URI
        registry = ClientRegistry(settings)
        is_valid, error_msg = registry.validate_redirect_uri(
            client_type, dcr_request.redirect_uris[0]
        )

        if not is_valid:
            logger.warning(
                "dcr_invalid_redirect_uri",
                client_type=client_type.value,
                redirect_uri=dcr_request.redirect_uris[0],
                error=error_msg,
            )
            # Don't fail hard - just log the warning and continue
            # The client will fail at Entra ID level if URI is truly invalid

        # Generate DCR response
        dcr_response = registry.get_dcr_response(
            client_type=client_type,
            requested_redirect_uri=dcr_request.redirect_uris[0],
        )

        logger.info(
            "dcr_success",
            client_type=client_type.value,
            client_id=dcr_response["client_id"],
            client_ip=client_ip,
        )

        return dcr_response

    except DCRError as e:
        logger.error("dcr_error", error=e.message, details=e.details)
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error": e.error_code,
                "error_description": e.message,
                "details": e.details,
            },
        ) from e

    except Exception as e:
        logger.error("dcr_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "An unexpected error occurred during client registration",
            },
        ) from e


@router.get(
    "/clients/{client_id}",
    summary="Get client information (not implemented)",
    description="Standard DCR endpoint for retrieving client info. Not implemented in this emulation.",
)
async def get_client_info(client_id: str) -> dict[str, Any]:
    """Get client information (not implemented).

    Args:
        client_id: Client ID

    Returns:
        Error message

    Raises:
        HTTPException: Always (not implemented)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error": "not_implemented",
            "error_description": (
                "Client info retrieval is not supported in DCR emulation mode. "
                "Clients are pre-registered in Entra ID."
            ),
        },
    )
