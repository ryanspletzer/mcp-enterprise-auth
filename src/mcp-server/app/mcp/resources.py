"""
MCP Resources Implementation.

Example resources demonstrating MCP resource capabilities:
- Static documents (README, API docs)
- Configuration files
- Data files (JSON, CSV)
"""

from typing import Dict, List

import structlog

from .models import Resource, ResourceContent, ResourceReadResponse

logger = structlog.get_logger()


# ============================================================================
# Resource Registry
# ============================================================================


class ResourceRegistry:
    """Registry of available MCP resources."""

    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._content: Dict[str, str] = {}
        self._register_builtin_resources()

    def _register_builtin_resources(self):
        """Register all built-in resources."""

        # README document
        self.register(
            Resource(
                uri="resource://documents/readme",
                name="README",
                description="Server README and documentation",
                mimeType="text/markdown",
            ),
            """# MCP Server with Enterprise Authentication

This server demonstrates proper enterprise authentication with:
- OAuth 2.0 / OpenID Connect
- Microsoft Entra ID integration
- JWT validation
- Multiple client support

## Features

- **DCR Emulation**: Dynamic client registration
- **Comprehensive JWT Validation**: Full security checks
- **Multiple OAuth Flows**: Auth Code, Client Credentials
- **MCP Protocol**: Tools, Resources, Prompts

## Example Tools

- get_weather: Get simulated weather data
- calculate: Perform mathematical calculations
- echo: Echo messages back
- random_number: Generate random numbers

## Resources

Access server documentation and configuration through MCP resources.
""",
        )

        # API Documentation
        self.register(
            Resource(
                uri="resource://documents/api-docs",
                name="API Documentation",
                description="MCP API documentation",
                mimeType="text/markdown",
            ),
            """# MCP API Documentation

## Endpoints

### Initialize
- **Method**: POST /mcp/initialize
- **Description**: Initialize MCP connection
- **Auth**: Required

### Tools
- **Method**: POST /mcp/tools/list
- **Description**: List available tools
- **Auth**: Required

- **Method**: POST /mcp/tools/call
- **Description**: Call a tool
- **Auth**: Required

### Resources
- **Method**: POST /mcp/resources/list
- **Description**: List available resources
- **Auth**: Required

- **Method**: POST /mcp/resources/read
- **Description**: Read a resource
- **Auth**: Required

### Prompts
- **Method**: POST /mcp/prompts/list
- **Description**: List available prompts
- **Auth**: Required

- **Method**: POST /mcp/prompts/get
- **Description**: Get a prompt
- **Auth**: Required
""",
        )

        # Server Configuration (public info only)
        self.register(
            Resource(
                uri="resource://config/server-info",
                name="Server Information",
                description="Public server configuration",
                mimeType="application/json",
            ),
            """{
  "name": "MCP Server with Enterprise Auth",
  "version": "1.0.0",
  "protocol_version": "2024-11-05",
  "capabilities": {
    "tools": true,
    "resources": true,
    "prompts": true,
    "logging": false
  },
  "authentication": {
    "type": "OAuth 2.0 / OpenID Connect",
    "provider": "Microsoft Entra ID",
    "flows": ["authorization_code", "client_credentials"],
    "pkce_required": true
  },
  "features": [
    "DCR emulation",
    "JWT validation",
    "Multi-client support",
    "Example tools and resources"
  ]
}""",
        )

        # Sample data - Weather locations
        self.register(
            Resource(
                uri="resource://data/weather-locations",
                name="Weather Locations",
                description="Sample weather location data",
                mimeType="application/json",
            ),
            """{
  "locations": [
    {
      "name": "San Francisco",
      "coordinates": {"lat": 37.7749, "lon": -122.4194},
      "timezone": "America/Los_Angeles"
    },
    {
      "name": "New York",
      "coordinates": {"lat": 40.7128, "lon": -74.0060},
      "timezone": "America/New_York"
    },
    {
      "name": "London",
      "coordinates": {"lat": 51.5074, "lon": -0.1278},
      "timezone": "Europe/London"
    },
    {
      "name": "Tokyo",
      "coordinates": {"lat": 35.6762, "lon": 139.6503},
      "timezone": "Asia/Tokyo"
    },
    {
      "name": "Sydney",
      "coordinates": {"lat": -33.8688, "lon": 151.2093},
      "timezone": "Australia/Sydney"
    }
  ]
}""",
        )

        # Sample data - Math constants
        self.register(
            Resource(
                uri="resource://data/math-constants",
                name="Mathematical Constants",
                description="Common mathematical constants",
                mimeType="application/json",
            ),
            """{
  "constants": {
    "pi": 3.141592653589793,
    "e": 2.718281828459045,
    "phi": 1.618033988749895,
    "sqrt2": 1.4142135623730951,
    "sqrt3": 1.7320508075688772,
    "ln2": 0.6931471805599453,
    "ln10": 2.302585092994046
  },
  "descriptions": {
    "pi": "Ratio of circle's circumference to diameter",
    "e": "Base of natural logarithm",
    "phi": "Golden ratio",
    "sqrt2": "Square root of 2",
    "sqrt3": "Square root of 3",
    "ln2": "Natural logarithm of 2",
    "ln10": "Natural logarithm of 10"
  }
}""",
        )

        # Example CSV data
        self.register(
            Resource(
                uri="resource://data/sample-data",
                name="Sample Data",
                description="Sample CSV data for testing",
                mimeType="text/csv",
            ),
            """id,name,value,category,timestamp
1,Alpha,42.5,A,2024-01-01T00:00:00Z
2,Beta,73.1,B,2024-01-02T00:00:00Z
3,Gamma,15.8,A,2024-01-03T00:00:00Z
4,Delta,91.2,C,2024-01-04T00:00:00Z
5,Epsilon,38.7,B,2024-01-05T00:00:00Z""",
        )

    def register(self, resource: Resource, content: str):
        """Register a resource with its content."""
        self._resources[resource.uri] = resource
        self._content[resource.uri] = content
        logger.info("resource_registered", resource_uri=resource.uri)

    def list_resources(self) -> List[Resource]:
        """Get list of all available resources."""
        return list(self._resources.values())

    def get_resource(self, uri: str) -> Resource:
        """Get a specific resource by URI."""
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")
        return self._resources[uri]

    def read_resource(self, uri: str) -> ResourceReadResponse:
        """Read the content of a resource."""
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")

        resource = self._resources[uri]
        content = self._content[uri]

        logger.info("resource_read", resource_uri=uri)

        return ResourceReadResponse(
            contents=[
                ResourceContent(
                    uri=uri,
                    mimeType=resource.mimeType,
                    text=content,
                )
            ]
        )


# ============================================================================
# Global Resource Registry Instance
# ============================================================================

resource_registry = ResourceRegistry()
