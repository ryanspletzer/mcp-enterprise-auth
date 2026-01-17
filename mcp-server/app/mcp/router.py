"""
MCP Protocol Router.

Implements all MCP protocol endpoints:
- initialize: Handshake and capability negotiation
- tools/list: List available tools
- tools/call: Execute a tool
- resources/list: List available resources
- resources/read: Read a resource
- prompts/list: List available prompts
- prompts/get: Get a prompt
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

import structlog

from app.auth.middleware import AuthContext, get_auth_context

from .models import (
    Implementation,
    InitializeRequest,
    InitializeResponse,
    MCP_PROTOCOL_VERSION,
    PromptsListRequest,
    PromptsListResponse,
    PromptGetRequest,
    PromptGetResponse,
    ResourceReadRequest,
    ResourceReadResponse,
    ResourcesListRequest,
    ResourcesListResponse,
    ServerCapabilities,
    ToolCallRequest,
    ToolCallResponse,
    ToolsListRequest,
    ToolsListResponse,
)
from .prompts import prompt_registry
from .resources import resource_registry
from .tools import tool_registry

logger = structlog.get_logger()

router = APIRouter(prefix="/mcp", tags=["MCP Protocol"])


# ============================================================================
# Initialize (Handshake)
# ============================================================================


@router.post("/initialize", response_model=InitializeResponse)
async def initialize(
    request: InitializeRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> InitializeResponse:
    """
    Initialize MCP connection and negotiate capabilities.

    This is the first call in the MCP protocol to establish the connection
    and exchange capability information.
    """
    logger.info(
        "mcp_initialize",
        client_name=request.clientInfo.name,
        client_version=request.clientInfo.version,
        protocol_version=request.protocolVersion,
        user_id=auth.identity.get("user_id") if auth.token_type == "user" else auth.identity.get("app_id"),
    )

    # Validate protocol version
    if request.protocolVersion != MCP_PROTOCOL_VERSION:
        logger.warning(
            "protocol_version_mismatch",
            requested=request.protocolVersion,
            supported=MCP_PROTOCOL_VERSION,
        )
        # Continue anyway for compatibility

    response = InitializeResponse(
        protocolVersion=MCP_PROTOCOL_VERSION,
        capabilities=ServerCapabilities(
            tools={"listChanged": True},
            resources={"listChanged": True, "subscribe": False},
            prompts={"listChanged": True},
            logging={},
        ),
        serverInfo=Implementation(
            name="MCP Server with Enterprise Auth",
            version="1.0.0",
        ),
        instructions="This MCP server provides example tools, resources, and prompts with enterprise-grade OAuth authentication.",
    )

    logger.info("mcp_initialize_complete", server_capabilities=response.capabilities)

    return response


# ============================================================================
# Tools
# ============================================================================


@router.post("/tools/list", response_model=ToolsListResponse)
async def list_tools(
    request: ToolsListRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> ToolsListResponse:
    """
    List all available tools.

    Returns a list of tools that can be called by the client.
    """
    logger.info("tools_list_requested", cursor=request.cursor)

    tools = tool_registry.list_tools()

    logger.info("tools_list_returned", count=len(tools))

    return ToolsListResponse(
        tools=tools,
        nextCursor=None,  # No pagination for now
    )


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> ToolCallResponse:
    """
    Call a tool with the provided arguments.

    Executes the specified tool and returns its result.
    """
    logger.info(
        "tool_call_requested",
        tool_name=request.name,
        user_id=auth.identity.get("user_id") if auth.token_type == "user" else auth.identity.get("app_id"),
    )

    try:
        response = tool_registry.call_tool(request.name, request.arguments or {})
        return response
    except ValueError as e:
        logger.error("tool_call_error", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("tool_call_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


# ============================================================================
# Resources
# ============================================================================


@router.post("/resources/list", response_model=ResourcesListResponse)
async def list_resources(
    request: ResourcesListRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> ResourcesListResponse:
    """
    List all available resources.

    Returns a list of resources that can be read by the client.
    """
    logger.info("resources_list_requested", cursor=request.cursor)

    resources = resource_registry.list_resources()

    logger.info("resources_list_returned", count=len(resources))

    return ResourcesListResponse(
        resources=resources,
        nextCursor=None,  # No pagination for now
    )


@router.post("/resources/read", response_model=ResourceReadResponse)
async def read_resource(
    request: ResourceReadRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> ResourceReadResponse:
    """
    Read the contents of a resource.

    Returns the content of the specified resource.
    """
    logger.info(
        "resource_read_requested",
        resource_uri=request.uri,
        user_id=auth.identity.get("user_id") if auth.token_type == "user" else auth.identity.get("app_id"),
    )

    try:
        response = resource_registry.read_resource(request.uri)
        return response
    except ValueError as e:
        logger.error("resource_read_error", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("resource_read_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resource read failed: {str(e)}")


# ============================================================================
# Prompts
# ============================================================================


@router.post("/prompts/list", response_model=PromptsListResponse)
async def list_prompts(
    request: PromptsListRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> PromptsListResponse:
    """
    List all available prompts.

    Returns a list of prompts that can be retrieved by the client.
    """
    logger.info("prompts_list_requested", cursor=request.cursor)

    prompts = prompt_registry.list_prompts()

    logger.info("prompts_list_returned", count=len(prompts))

    return PromptsListResponse(
        prompts=prompts,
        nextCursor=None,  # No pagination for now
    )


@router.post("/prompts/get", response_model=PromptGetResponse)
async def get_prompt(
    request: PromptGetRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> PromptGetResponse:
    """
    Get a prompt with the provided arguments.

    Returns the generated prompt messages.
    """
    logger.info(
        "prompt_get_requested",
        prompt_name=request.name,
        user_id=auth.identity.get("user_id") if auth.token_type == "user" else auth.identity.get("app_id"),
    )

    try:
        response = prompt_registry.generate_prompt(request.name, request.arguments or {})
        return response
    except ValueError as e:
        logger.error("prompt_get_error", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("prompt_get_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {str(e)}")


# ============================================================================
# Health Check for MCP
# ============================================================================


@router.get("/health")
async def mcp_health() -> JSONResponse:
    """MCP protocol health check."""
    return JSONResponse(
        content={
            "status": "healthy",
            "protocol_version": MCP_PROTOCOL_VERSION,
            "tools_count": len(tool_registry.list_tools()),
            "resources_count": len(resource_registry.list_resources()),
            "prompts_count": len(prompt_registry.list_prompts()),
        }
    )
