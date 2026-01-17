"""Client type detection for DCR emulation."""

import re
from enum import Enum
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class ClientType(str, Enum):
    """Supported client types."""

    VSCODE = "vscode"
    CLAUDE_DESKTOP = "claude-desktop"
    CLAUDE_CODE = "claude-code"
    CHATGPT = "chatgpt"
    GENERIC = "generic"


class ClientDetector:
    """Detects MCP client type from request metadata.

    Uses redirect_uri, User-Agent, and other context clues to identify
    the client type and return the appropriate pre-registered client_id.
    """

    # Redirect URI patterns for each client type
    REDIRECT_URI_PATTERNS = {
        ClientType.VSCODE: [
            re.compile(r"^vscode://", re.IGNORECASE),
            re.compile(r"^vscode-insiders://", re.IGNORECASE),
        ],
        ClientType.CLAUDE_DESKTOP: [
            re.compile(r"^claude://", re.IGNORECASE),
        ],
        ClientType.CLAUDE_CODE: [
            re.compile(r"^http://localhost:\d+/callback$", re.IGNORECASE),
            re.compile(r"^http://127\.0\.0\.1:\d+/callback$", re.IGNORECASE),
        ],
        ClientType.CHATGPT: [
            re.compile(r"^https?://chat\.openai\.com", re.IGNORECASE),
            re.compile(r"^https?://.*openai.*", re.IGNORECASE),
        ],
    }

    # User-Agent patterns for each client type
    USER_AGENT_PATTERNS = {
        ClientType.VSCODE: [
            re.compile(r"vscode", re.IGNORECASE),
            re.compile(r"visual\s*studio\s*code", re.IGNORECASE),
        ],
        ClientType.CLAUDE_DESKTOP: [
            re.compile(r"claude.*desktop", re.IGNORECASE),
            re.compile(r"anthropic.*desktop", re.IGNORECASE),
        ],
        ClientType.CLAUDE_CODE: [
            re.compile(r"claude.*code", re.IGNORECASE),
            re.compile(r"claude.*cli", re.IGNORECASE),
            re.compile(r"anthropic.*cli", re.IGNORECASE),
        ],
        ClientType.CHATGPT: [
            re.compile(r"chatgpt", re.IGNORECASE),
            re.compile(r"openai", re.IGNORECASE),
        ],
    }

    def detect(
        self,
        redirect_uri: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> ClientType:
        """Detect client type from request metadata.

        Detection priority:
        1. Redirect URI (most reliable)
        2. User-Agent
        3. Client name
        4. Default to GENERIC

        Args:
            redirect_uri: OAuth redirect URI
            user_agent: User-Agent header
            client_name: Client name from DCR request

        Returns:
            Detected client type
        """
        # Try redirect_uri first (most reliable)
        if redirect_uri:
            client_type = self._detect_by_redirect_uri(redirect_uri)
            if client_type:
                logger.info(
                    "client_detected_by_redirect_uri",
                    client_type=client_type.value,
                    redirect_uri=redirect_uri,
                )
                return client_type

        # Try User-Agent
        if user_agent:
            client_type = self._detect_by_user_agent(user_agent)
            if client_type:
                logger.info(
                    "client_detected_by_user_agent",
                    client_type=client_type.value,
                    user_agent=user_agent,
                )
                return client_type

        # Try client name
        if client_name:
            client_type = self._detect_by_client_name(client_name)
            if client_type:
                logger.info(
                    "client_detected_by_client_name",
                    client_type=client_type.value,
                    client_name=client_name,
                )
                return client_type

        # Default to generic
        logger.info(
            "client_detected_generic",
            redirect_uri=redirect_uri,
            user_agent=user_agent,
            client_name=client_name,
        )
        return ClientType.GENERIC

    def _detect_by_redirect_uri(self, redirect_uri: str) -> Optional[ClientType]:
        """Detect client type by redirect URI.

        Args:
            redirect_uri: OAuth redirect URI

        Returns:
            Client type or None if not detected
        """
        for client_type, patterns in self.REDIRECT_URI_PATTERNS.items():
            for pattern in patterns:
                if pattern.match(redirect_uri):
                    # Special case: localhost could be Claude Code or generic
                    if client_type == ClientType.CLAUDE_CODE:
                        # Need additional confirmation via User-Agent
                        return client_type
                    return client_type
        return None

    def _detect_by_user_agent(self, user_agent: str) -> Optional[ClientType]:
        """Detect client type by User-Agent.

        Args:
            user_agent: User-Agent header

        Returns:
            Client type or None if not detected
        """
        for client_type, patterns in self.USER_AGENT_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(user_agent):
                    return client_type
        return None

    def _detect_by_client_name(self, client_name: str) -> Optional[ClientType]:
        """Detect client type by client name.

        Args:
            client_name: Client name from request

        Returns:
            Client type or None if not detected
        """
        client_name_lower = client_name.lower()

        if "vscode" in client_name_lower or "visual studio code" in client_name_lower:
            return ClientType.VSCODE
        elif "claude" in client_name_lower and "desktop" in client_name_lower:
            return ClientType.CLAUDE_DESKTOP
        elif "claude" in client_name_lower and (
            "code" in client_name_lower or "cli" in client_name_lower
        ):
            return ClientType.CLAUDE_CODE
        elif "chatgpt" in client_name_lower or "openai" in client_name_lower:
            return ClientType.CHATGPT

        return None

    def get_confidence_score(
        self,
        redirect_uri: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> tuple[ClientType, float]:
        """Get client type with confidence score.

        Args:
            redirect_uri: OAuth redirect URI
            user_agent: User-Agent header
            client_name: Client name from DCR request

        Returns:
            Tuple of (client_type, confidence_score)
            Confidence: 0.0 (generic fallback) to 1.0 (certain match)
        """
        confidence = 0.0
        detected_type = ClientType.GENERIC

        # Redirect URI detection (high confidence)
        if redirect_uri:
            uri_type = self._detect_by_redirect_uri(redirect_uri)
            if uri_type and uri_type != ClientType.GENERIC:
                detected_type = uri_type
                confidence = 0.9  # High confidence for redirect URI match

        # User-Agent detection (medium confidence, can supplement)
        if user_agent:
            ua_type = self._detect_by_user_agent(user_agent)
            if ua_type:
                if detected_type == ClientType.GENERIC:
                    detected_type = ua_type
                    confidence = 0.7  # Medium confidence for User-Agent match
                elif detected_type == ua_type:
                    confidence = min(1.0, confidence + 0.1)  # Boost if matches

        # Client name detection (lower confidence, can supplement)
        if client_name:
            name_type = self._detect_by_client_name(client_name)
            if name_type:
                if detected_type == ClientType.GENERIC:
                    detected_type = name_type
                    confidence = 0.5  # Lower confidence for name match
                elif detected_type == name_type:
                    confidence = min(1.0, confidence + 0.05)  # Small boost if matches

        return detected_type, confidence
