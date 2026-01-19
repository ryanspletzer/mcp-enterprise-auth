"""Client registry for DCR emulation.

Maps client types to pre-registered app credentials in Entra ID.
"""

from typing import Any, Optional

from app.config import Settings
from app.dcr.client_detector import ClientType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ClientRegistry:
    """Registry of pre-registered clients in Entra ID.

    Maps detected client types to their corresponding app registrations.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize client registry.

        Args:
            settings: Application settings
        """
        self.settings = settings

        # Build client mapping from settings
        self.client_mapping = {
            ClientType.VSCODE: {
                "client_id": settings.VSCODE_CLIENT_ID,
                "client_type": "public",
                "redirect_uris": ["vscode://mcp-auth/callback"],
                "name": "VS Code MCP Client",
            },
            ClientType.CLAUDE_DESKTOP: {
                "client_id": settings.CLAUDE_DESKTOP_CLIENT_ID,
                "client_type": "public",
                "redirect_uris": ["claude://mcp-auth/callback"],
                "name": "Claude Desktop MCP Client",
            },
            ClientType.CLAUDE_CODE: {
                "client_id": settings.CLAUDE_CODE_CLIENT_ID,
                "client_type": "public",
                "redirect_uris": ["http://localhost:*/callback", "http://127.0.0.1:*/callback"],
                "name": "Claude Code MCP Client",
            },
            ClientType.CHATGPT: {
                "client_id": settings.CHATGPT_CLIENT_ID,
                "client_type": "public",
                "redirect_uris": ["https://chat.openai.com/mcp/callback"],
                "name": "ChatGPT MCP Client",
            },
            ClientType.GENERIC: {
                "client_id": settings.GENERIC_CLIENT_ID,
                "client_type": "public",
                "redirect_uris": [
                    "http://localhost:*/callback",
                    "http://127.0.0.1:*/callback",
                ],
                "name": "Generic MCP Client",
            },
        }

        logger.info(
            "client_registry_initialized",
            num_clients=len(self.client_mapping),
            client_types=[ct.value for ct in self.client_mapping.keys()],
        )

    def get_client_info(self, client_type: ClientType) -> dict[str, Any]:
        """Get client information for a detected client type.

        Args:
            client_type: Detected client type

        Returns:
            Client information dict with:
            - client_id: The pre-registered client ID from Entra ID
            - client_type: "public" or "confidential"
            - redirect_uris: Allowed redirect URIs
            - name: Client display name
        """
        client_info = self.client_mapping.get(client_type)

        if not client_info:
            logger.warning(
                "client_type_not_found_falling_back_to_generic",
                requested_type=client_type.value,
            )
            client_info = self.client_mapping[ClientType.GENERIC]

        logger.info(
            "client_info_retrieved",
            client_type=client_type.value,
            client_id=client_info["client_id"],
            client_name=client_info["name"],
        )

        return client_info.copy()

    def get_dcr_response(
        self,
        client_type: ClientType,
        requested_redirect_uri: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build a DCR response for the client.

        Returns OAuth client metadata in DCR format, compatible with
        RFC 7591 (OAuth 2.0 Dynamic Client Registration Protocol).

        Args:
            client_type: Detected client type
            requested_redirect_uri: The redirect URI from the request

        Returns:
            DCR response dict
        """
        client_info = self.get_client_info(client_type)

        # Build OAuth endpoints
        authority = self.settings.ENTRA_AUTHORITY
        tenant_id = self.settings.ENTRA_TENANT_ID

        response = {
            # Client credentials
            "client_id": client_info["client_id"],
            "client_name": client_info["name"],
            "client_type": client_info["client_type"],
            # OAuth endpoints
            "authorization_endpoint": f"{authority}/oauth2/v2.0/authorize",
            "token_endpoint": f"{authority}/oauth2/v2.0/token",
            "end_session_endpoint": f"{authority}/oauth2/v2.0/logout",
            "issuer": f"{authority}/v2.0",
            "jwks_uri": f"{authority}/discovery/v2.0/keys",
            # Redirect URIs
            "redirect_uris": client_info["redirect_uris"],
            # Grant types and response types
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            # Token endpoint auth method (none for public clients)
            "token_endpoint_auth_method": "none",
            # Scopes
            "scope": f"{self.settings.MCP_SERVER_APP_ID}/.default openid profile email",
            # Additional metadata
            "tenant_id": tenant_id,
            # Note about PKCE
            "require_pkce": True,
        }

        # If a specific redirect URI was requested, include it
        if requested_redirect_uri:
            response["requested_redirect_uri"] = requested_redirect_uri

        logger.info(
            "dcr_response_generated",
            client_type=client_type.value,
            client_id=client_info["client_id"],
        )

        return response

    def validate_redirect_uri(
        self, client_type: ClientType, redirect_uri: str
    ) -> tuple[bool, Optional[str]]:
        """Validate if redirect URI is allowed for client type.

        Args:
            client_type: Client type
            redirect_uri: Redirect URI to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        client_info = self.client_mapping.get(client_type)
        if not client_info:
            return False, f"Unknown client type: {client_type}"

        allowed_patterns = client_info["redirect_uris"]

        # Check exact matches
        if redirect_uri in allowed_patterns:
            return True, None

        # Check wildcard patterns (e.g., http://localhost:*/callback)
        for pattern in allowed_patterns:
            if "*" in pattern:
                # Simple wildcard matching
                pattern_regex = pattern.replace("*", r"\d+")
                import re

                if re.match(f"^{pattern_regex}$", redirect_uri):
                    return True, None

        return False, f"Redirect URI not allowed for {client_info['name']}"
