"""Tests for DCR client detector module."""

import pytest

from app.dcr.client_detector import ClientDetector, ClientType


@pytest.mark.unit
@pytest.mark.dcr
class TestClientDetector:
    """Test ClientDetector class."""

    @pytest.fixture
    def detector(self) -> ClientDetector:
        """Create client detector instance."""
        return ClientDetector()

    def test_detect_vscode_by_redirect_uri(self, detector):
        """Test VS Code detection by redirect URI."""
        client_type = detector.detect(redirect_uri="vscode://mcp-auth/callback")
        assert client_type == ClientType.VSCODE

    def test_detect_vscode_insiders_by_redirect_uri(self, detector):
        """Test VS Code Insiders detection by redirect URI."""
        client_type = detector.detect(redirect_uri="vscode-insiders://mcp-auth/callback")
        assert client_type == ClientType.VSCODE

    def test_detect_claude_desktop_by_redirect_uri(self, detector):
        """Test Claude Desktop detection by redirect URI."""
        client_type = detector.detect(redirect_uri="claude://mcp-auth/callback")
        assert client_type == ClientType.CLAUDE_DESKTOP

    def test_detect_claude_code_by_redirect_uri(self, detector):
        """Test Claude Code detection by redirect URI."""
        client_type = detector.detect(redirect_uri="http://localhost:8080/callback")
        assert client_type == ClientType.CLAUDE_CODE

    def test_detect_chatgpt_by_redirect_uri(self, detector):
        """Test ChatGPT detection by redirect URI."""
        client_type = detector.detect(redirect_uri="https://chat.openai.com/mcp/callback")
        assert client_type == ClientType.CHATGPT

    def test_detect_vscode_by_user_agent(self, detector):
        """Test VS Code detection by User-Agent."""
        client_type = detector.detect(user_agent="VSCode-MCP/1.0")
        assert client_type == ClientType.VSCODE

    def test_detect_claude_desktop_by_user_agent(self, detector):
        """Test Claude Desktop detection by User-Agent."""
        client_type = detector.detect(user_agent="Claude Desktop/1.0")
        assert client_type == ClientType.CLAUDE_DESKTOP

    def test_detect_claude_code_by_user_agent(self, detector):
        """Test Claude Code detection by User-Agent."""
        client_type = detector.detect(user_agent="Claude-CLI/1.0")
        assert client_type == ClientType.CLAUDE_CODE

    def test_detect_chatgpt_by_user_agent(self, detector):
        """Test ChatGPT detection by User-Agent."""
        client_type = detector.detect(user_agent="ChatGPT/1.0")
        assert client_type == ClientType.CHATGPT

    def test_detect_by_client_name(self, detector):
        """Test detection by client name."""
        client_type = detector.detect(client_name="VS Code MCP Client")
        assert client_type == ClientType.VSCODE

    def test_detect_generic_fallback(self, detector):
        """Test generic fallback for unknown client."""
        client_type = detector.detect(
            redirect_uri="http://unknown.com/callback",
            user_agent="Unknown Client/1.0",
        )
        assert client_type == ClientType.GENERIC

    def test_detect_priority_redirect_uri_over_user_agent(self, detector):
        """Test redirect URI has priority over User-Agent."""
        # VS Code redirect URI, but ChatGPT user agent
        client_type = detector.detect(
            redirect_uri="vscode://mcp-auth/callback",
            user_agent="ChatGPT/1.0",
        )
        assert client_type == ClientType.VSCODE

    def test_get_confidence_score_high_for_redirect_uri(self, detector):
        """Test high confidence for redirect URI match."""
        client_type, confidence = detector.get_confidence_score(
            redirect_uri="vscode://mcp-auth/callback"
        )
        assert client_type == ClientType.VSCODE
        assert confidence >= 0.9

    def test_get_confidence_score_medium_for_user_agent(self, detector):
        """Test medium confidence for User-Agent match."""
        client_type, confidence = detector.get_confidence_score(user_agent="VSCode-MCP/1.0")
        assert client_type == ClientType.VSCODE
        assert 0.7 <= confidence < 0.9

    def test_get_confidence_score_boost_for_multiple_matches(self, detector):
        """Test confidence boost when multiple indicators match."""
        client_type, confidence = detector.get_confidence_score(
            redirect_uri="vscode://mcp-auth/callback",
            user_agent="VSCode-MCP/1.0",
        )
        assert client_type == ClientType.VSCODE
        assert confidence >= 0.9

    def test_get_confidence_score_low_for_generic(self, detector):
        """Test low confidence for generic fallback."""
        client_type, confidence = detector.get_confidence_score(
            redirect_uri="http://unknown.com/callback"
        )
        assert client_type == ClientType.GENERIC
        assert confidence == 0.0


@pytest.mark.unit
@pytest.mark.dcr
class TestClientDetectorEdgeCases:
    """Test ClientDetector edge cases."""

    @pytest.fixture
    def detector(self) -> ClientDetector:
        """Create client detector instance."""
        return ClientDetector()

    def test_detect_case_insensitive_redirect_uri(self, detector):
        """Test case-insensitive redirect URI matching."""
        client_type = detector.detect(redirect_uri="VSCODE://mcp-auth/callback")
        assert client_type == ClientType.VSCODE

    def test_detect_case_insensitive_user_agent(self, detector):
        """Test case-insensitive User-Agent matching."""
        client_type = detector.detect(user_agent="vscode-mcp/1.0")
        assert client_type == ClientType.VSCODE

    def test_detect_with_none_values(self, detector):
        """Test detection with None values."""
        client_type = detector.detect(redirect_uri=None, user_agent=None)
        assert client_type == ClientType.GENERIC

    def test_detect_with_empty_strings(self, detector):
        """Test detection with empty strings."""
        client_type = detector.detect(redirect_uri="", user_agent="")
        assert client_type == ClientType.GENERIC

    def test_detect_localhost_with_claude_user_agent(self, detector):
        """Test localhost redirect with Claude user agent detects Claude Code."""
        client_type = detector.detect(
            redirect_uri="http://localhost:8080/callback",
            user_agent="Claude-CLI/1.0",
        )
        assert client_type == ClientType.CLAUDE_CODE

    def test_detect_localhost_without_claude_user_agent(self, detector):
        """Test localhost redirect without Claude user agent."""
        client_type = detector.detect(
            redirect_uri="http://localhost:8080/callback",
            user_agent="Other Client/1.0",
        )
        # Should still detect as Claude Code based on redirect_uri
        assert client_type == ClientType.CLAUDE_CODE
