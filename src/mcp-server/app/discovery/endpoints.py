"""OAuth 2.0 Protected Resource Metadata endpoints (RFC 9728)."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """
    OAuth 2.0 Protected Resource Metadata endpoint (RFC 9728).

    Returns metadata about this resource server (MCP server) to help
    clients understand how to access protected resources.

    This endpoint advertises:
    - The resource server identifier
    - Authorization servers that issue tokens for this resource
    - Token delivery methods supported
    - Scopes and permissions required
    - Additional resource server capabilities
    """
    scope_prefix = settings.MCP_SERVER_SCOPE_PREFIX or settings.MCP_SERVER_APP_ID

    metadata = {
        # Resource server identifier (RFC 9728 Section 2)
        "resource": settings.MCP_SERVER_APP_ID,
        # Authorization servers that issue tokens for this resource (RFC 9728 Section 2.1)
        "authorization_servers": [settings.ENTRA_AUTHORITY],
        # Bearer token methods supported (RFC 9728 Section 2.2)
        "bearer_methods_supported": ["header"],  # Only Authorization: Bearer header
        # Scopes available at this resource server (RFC 9728 Section 2.3)
        "scopes_supported": [
            f"{scope_prefix}/.default",
            f"{scope_prefix}/mcp.read",
            f"{scope_prefix}/mcp.write",
        ],
        # JWT signing algorithms supported for resource authentication (RFC 9728 Section 2.4)
        "resource_signing_alg_values_supported": ["RS256"],
        # Additional capabilities
        "capabilities": {
            "mcp_protocol": "2024-11-05",
            "dcr_emulation": True,
            "pkce_required": True,
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "token_types_supported": ["user", "app"],
        },
        # MCP-specific metadata
        "mcp": {
            "version": "1.0.0",
            "endpoints": {
                "initialize": f"{settings.MCP_SERVER_BASE_URL}/mcp/initialize",
                "tools_list": f"{settings.MCP_SERVER_BASE_URL}/mcp/tools/list",
                "tools_call": f"{settings.MCP_SERVER_BASE_URL}/mcp/tools/call",
                "resources_list": f"{settings.MCP_SERVER_BASE_URL}/mcp/resources/list",
                "resources_read": f"{settings.MCP_SERVER_BASE_URL}/mcp/resources/read",
                "prompts_list": f"{settings.MCP_SERVER_BASE_URL}/mcp/prompts/list",
                "prompts_get": f"{settings.MCP_SERVER_BASE_URL}/mcp/prompts/get",
            },
            "dcr_endpoint": f"{settings.MCP_SERVER_BASE_URL}/dcr/register",
        },
        # Required permissions for different operations
        "permissions": {
            "read": {
                "delegated_scopes": [f"{scope_prefix}/mcp.read"],
                "application_roles": ["MCP.Read.All"],
            },
            "write": {
                "delegated_scopes": [f"{scope_prefix}/mcp.write"],
                "application_roles": ["MCP.ReadWrite.All"],
            },
        },
    }

    logger.debug("oauth_protected_resource_metadata_served")

    return metadata


@router.get("/.well-known/mcp-server")
async def mcp_server_metadata(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """
    MCP Server Metadata endpoint (custom).

    Provides MCP-specific metadata about this server's capabilities,
    combining OAuth resource metadata with MCP protocol information.

    This is a convenience endpoint that combines RFC 9728 metadata
    with MCP-specific information in a single response.
    """
    scope_prefix = settings.MCP_SERVER_SCOPE_PREFIX or settings.MCP_SERVER_APP_ID

    metadata = {
        "name": "MCP Server with Enterprise Authentication",
        "version": "1.0.0",
        "mcp_protocol_version": "2024-11-05",
        # OAuth 2.0 / OpenID Connect authentication
        "authentication": {
            "type": "OAuth 2.0 / OpenID Connect",
            "provider": "Microsoft Entra ID",
            "resource_identifier": settings.MCP_SERVER_APP_ID,
            "authorization_server": settings.ENTRA_AUTHORITY,
            "token_endpoint": f"{settings.ENTRA_AUTHORITY}/oauth2/v2.0/token",
            "authorization_endpoint": f"{settings.ENTRA_AUTHORITY}/oauth2/v2.0/authorize",
            "discovery_endpoint": f"{settings.ENTRA_AUTHORITY}/.well-known/openid-configuration",
            "jwks_uri": settings.ENTRA_JWKS_URL,
            "flows_supported": ["authorization_code", "client_credentials"],
            "pkce_required": True,
            "token_delivery": ["header"],  # Authorization: Bearer <token>
        },
        # DCR (Dynamic Client Registration) emulation
        "dcr": {
            "enabled": settings.ENABLE_DCR_ENDPOINT,
            "endpoint": f"{settings.MCP_SERVER_BASE_URL}/dcr/register",
            "description": "DCR emulation with intelligent client detection",
            "supported_clients": [
                "VS Code",
                "Claude Desktop",
                "Claude Code",
                "ChatGPT",
                "Generic MCP Clients",
            ],
        },
        # MCP protocol endpoints
        "endpoints": {
            "initialize": f"{settings.MCP_SERVER_BASE_URL}/mcp/initialize",
            "tools": {
                "list": f"{settings.MCP_SERVER_BASE_URL}/mcp/tools/list",
                "call": f"{settings.MCP_SERVER_BASE_URL}/mcp/tools/call",
            },
            "resources": {
                "list": f"{settings.MCP_SERVER_BASE_URL}/mcp/resources/list",
                "read": f"{settings.MCP_SERVER_BASE_URL}/mcp/resources/read",
            },
            "prompts": {
                "list": f"{settings.MCP_SERVER_BASE_URL}/mcp/prompts/list",
                "get": f"{settings.MCP_SERVER_BASE_URL}/mcp/prompts/get",
            },
        },
        # Required scopes and roles
        "permissions": {
            "user_delegated": {
                "read": f"{scope_prefix}/mcp.read",
                "write": f"{scope_prefix}/mcp.write",
            },
            "application": {
                "read": "MCP.Read.All",
                "write": "MCP.ReadWrite.All",
            },
        },
        # Links to documentation
        "documentation": {
            "api": f"{settings.MCP_SERVER_BASE_URL}/docs",
            "openapi": f"{settings.MCP_SERVER_BASE_URL}/openapi.json",
        },
    }

    logger.debug("mcp_server_metadata_served")

    return metadata
