"""
MCP Protocol Models and Schemas.

Defines the data structures for the Model Context Protocol including:
- Initialize request/response
- Tools (list, call)
- Resources (list, read)
- Prompts (list, get)
- Notifications

Following the MCP specification.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ============================================================================
# MCP Protocol Version
# ============================================================================

MCP_PROTOCOL_VERSION = "2024-11-05"


# ============================================================================
# Common Types
# ============================================================================


class ToolInputSchema(BaseModel):
    """JSON Schema for tool input parameters."""

    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = False


class Implementation(BaseModel):
    """Implementation details for client or server."""

    name: str
    version: str


# ============================================================================
# Initialize Request/Response
# ============================================================================


class ClientCapabilities(BaseModel):
    """Capabilities advertised by the client."""

    roots: Optional[Dict[str, bool]] = None
    sampling: Optional[Dict[str, bool]] = None
    experimental: Optional[Dict[str, Any]] = None


class InitializeRequest(BaseModel):
    """Initialize request from client."""

    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class ServerCapabilities(BaseModel):
    """Capabilities advertised by the server."""

    tools: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    resources: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    prompts: Optional[Dict[str, bool]] = Field(default_factory=lambda: {"listChanged": True})
    logging: Optional[Dict[str, bool]] = None
    experimental: Optional[Dict[str, Any]] = None


class InitializeResponse(BaseModel):
    """Initialize response from server."""

    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: Optional[str] = None


# ============================================================================
# Tools
# ============================================================================


class Tool(BaseModel):
    """Tool definition."""

    name: str
    description: str
    inputSchema: ToolInputSchema


class ToolsListRequest(BaseModel):
    """Request to list available tools."""

    cursor: Optional[str] = None


class ToolsListResponse(BaseModel):
    """Response with list of tools."""

    tools: List[Tool]
    nextCursor: Optional[str] = None


class ToolCallRequest(BaseModel):
    """Request to call a tool."""

    name: str
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ToolContent(BaseModel):
    """Content returned by a tool."""

    type: str  # "text", "image", "resource"
    text: Optional[str] = None
    data: Optional[str] = None  # Base64 encoded for images
    mimeType: Optional[str] = None
    uri: Optional[str] = None  # For resource references


class ToolCallResponse(BaseModel):
    """Response from calling a tool."""

    content: List[ToolContent]
    isError: bool = False


# ============================================================================
# Resources
# ============================================================================


class Resource(BaseModel):
    """Resource definition."""

    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class ResourcesListRequest(BaseModel):
    """Request to list available resources."""

    cursor: Optional[str] = None


class ResourcesListResponse(BaseModel):
    """Response with list of resources."""

    resources: List[Resource]
    nextCursor: Optional[str] = None


class ResourceReadRequest(BaseModel):
    """Request to read a resource."""

    uri: str


class ResourceContent(BaseModel):
    """Content of a resource."""

    uri: str
    mimeType: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[str] = None  # Base64 encoded binary data


class ResourceReadResponse(BaseModel):
    """Response with resource contents."""

    contents: List[ResourceContent]


# ============================================================================
# Prompts
# ============================================================================


class PromptArgument(BaseModel):
    """Prompt argument definition."""

    name: str
    description: Optional[str] = None
    required: bool = False


class Prompt(BaseModel):
    """Prompt definition."""

    name: str
    description: Optional[str] = None
    arguments: List[PromptArgument] = Field(default_factory=list)


class PromptsListRequest(BaseModel):
    """Request to list available prompts."""

    cursor: Optional[str] = None


class PromptsListResponse(BaseModel):
    """Response with list of prompts."""

    prompts: List[Prompt]
    nextCursor: Optional[str] = None


class PromptGetRequest(BaseModel):
    """Request to get a prompt."""

    name: str
    arguments: Optional[Dict[str, str]] = Field(default_factory=dict)


class PromptMessage(BaseModel):
    """Message in a prompt."""

    role: str  # "user" or "assistant"
    content: Dict[str, Any]  # Text or image content


class PromptGetResponse(BaseModel):
    """Response with prompt messages."""

    description: Optional[str] = None
    messages: List[PromptMessage]


# ============================================================================
# Notifications
# ============================================================================


class NotificationType(str, Enum):
    """Types of notifications."""

    TOOLS_LIST_CHANGED = "notifications/tools/list_changed"
    RESOURCES_LIST_CHANGED = "notifications/resources/list_changed"
    PROMPTS_LIST_CHANGED = "notifications/prompts/list_changed"
    PROGRESS = "notifications/progress"
    MESSAGE = "notifications/message"


class ProgressNotification(BaseModel):
    """Progress notification."""

    progressToken: str
    progress: float  # 0.0 to 1.0
    total: Optional[float] = None


class MessageNotification(BaseModel):
    """Message notification."""

    level: str  # "debug", "info", "warning", "error"
    logger: Optional[str] = None
    data: Any


class LoggingLevel(str, Enum):
    """Logging levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============================================================================
# Error Response
# ============================================================================


class MCPError(BaseModel):
    """MCP error response."""

    code: int
    message: str
    data: Optional[Any] = None


# ============================================================================
# Request/Response Envelope (JSON-RPC style)
# ============================================================================


class MCPRequest(BaseModel):
    """MCP request envelope."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP response envelope."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None


class MCPNotification(BaseModel):
    """MCP notification (no response expected)."""

    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
