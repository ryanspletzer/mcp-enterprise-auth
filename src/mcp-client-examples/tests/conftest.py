"""
Shared pytest fixtures for MCP client tests.

This module provides common fixtures used across all client tests:
- Mock HTTP responses for Entra ID endpoints
- Mock MCP server responses
- Test configuration
- JWT token generation
- Dynamic module loading for client classes (to avoid import conflicts)
"""

import hashlib
import importlib.util
import secrets
import sys
from base64 import urlsafe_b64encode
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from httpx import Response


# ============================================================================
# Dynamic Module Loading Helpers
# ============================================================================


def load_client_module(module_name: str, client_dir: str):
    """
    Dynamically load a client module with a unique name to avoid caching conflicts.

    Args:
        module_name: Unique name for the module in sys.modules
        client_dir: Directory name containing the client.py file

    Returns:
        The loaded module
    """
    client_path = Path(__file__).parent.parent / client_dir / "client.py"

    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, client_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ============================================================================
# Client Class Fixtures (dynamically loaded to avoid import conflicts)
# ============================================================================


@pytest.fixture(scope="session")
def public_client_with_client_id_module():
    """Dynamically load the public-client-with-client-id module."""
    return load_client_module(
        "mcp_public_client_with_creds",
        "public-client-with-client-id"
    )


@pytest.fixture(scope="session")
def MCPPublicClientWithCreds(public_client_with_client_id_module):
    """Get MCPPublicClientWithCreds class from dynamically loaded module."""
    return public_client_with_client_id_module.MCPPublicClientWithCreds


@pytest.fixture(scope="session")
def OAuthCallbackHandlerWithCreds(public_client_with_client_id_module):
    """Get OAuthCallbackHandler class from public-client-with-client-id module."""
    return public_client_with_client_id_module.OAuthCallbackHandler


@pytest.fixture(scope="session")
def public_client_without_client_id_module():
    """Dynamically load the public-client-without-client-id module."""
    return load_client_module(
        "mcp_public_client_no_creds",
        "public-client-without-client-id"
    )


@pytest.fixture(scope="session")
def MCPPublicClient(public_client_without_client_id_module):
    """Get MCPPublicClient class from dynamically loaded module."""
    return public_client_without_client_id_module.MCPPublicClient


@pytest.fixture(scope="session")
def OAuthCallbackHandler(public_client_without_client_id_module):
    """Get OAuthCallbackHandler class from public-client-without-client-id module."""
    return public_client_without_client_id_module.OAuthCallbackHandler


@pytest.fixture(scope="session")
def confidential_client_module():
    """Dynamically load the confidential-client module."""
    return load_client_module(
        "mcp_confidential_client",
        "confidential-client"
    )


@pytest.fixture(scope="session")
def MCPConfidentialClient(confidential_client_module):
    """Get MCPConfidentialClient class from dynamically loaded module."""
    return confidential_client_module.MCPConfidentialClient


@pytest.fixture(scope="session")
def service_principal_module():
    """Dynamically load the service-principal module."""
    return load_client_module(
        "mcp_service_principal_client",
        "service-principal"
    )


@pytest.fixture(scope="session")
def MCPServicePrincipalClient(service_principal_module):
    """Get MCPServicePrincipalClient class from dynamically loaded module."""
    return service_principal_module.MCPServicePrincipalClient


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def test_config() -> Dict[str, str]:
    """Test configuration for all clients."""
    return {
        "client_id": "test-client-id-12345",
        "client_secret": "test-client-secret-abc123",
        "tenant_id": "test-tenant-id-67890",
        "mcp_server_url": "http://localhost:8000",
        "redirect_uri": "http://localhost:8080/callback",
        "scope": "api://mcp-server/.default",
    }


@pytest.fixture
def authority(test_config: Dict[str, str]) -> str:
    """Entra ID authority URL."""
    return f"https://login.microsoftonline.com/{test_config['tenant_id']}"


@pytest.fixture
def token_endpoint(authority: str) -> str:
    """Entra ID token endpoint."""
    return f"{authority}/oauth2/v2.0/token"


@pytest.fixture
def authorization_endpoint(authority: str) -> str:
    """Entra ID authorization endpoint."""
    return f"{authority}/oauth2/v2.0/authorize"


# ============================================================================
# PKCE Fixtures
# ============================================================================


@pytest.fixture
def pkce_verifier() -> str:
    """Generate PKCE code verifier."""
    return urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")


@pytest.fixture
def pkce_challenge(pkce_verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    challenge_bytes = hashlib.sha256(pkce_verifier.encode("utf-8")).digest()
    return urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")


@pytest.fixture
def state_value() -> str:
    """Generate OAuth state parameter."""
    return secrets.token_urlsafe(32)


# ============================================================================
# Token Fixtures
# ============================================================================


@pytest.fixture
def mock_user_token() -> str:
    """Mock user access token (JWT structure not validated in clients)."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhcGk6Ly9tY3Atc2VydmVyIiwiaXNzIjoiaHR0cHM6Ly9sb2dpbi5taWNyb3NvZnRvbmxpbmUuY29tL3Rlc3QtdGVuYW50L3YyLjAiLCJpYXQiOjE3MDU1MDAwMDAsImV4cCI6MTcwNTUwMzU5OSwibmJmIjoxNzA1NTAwMDAwLCJzY3AiOiJtY3AucmVhZCBtY3Aud3JpdGUiLCJuYW1lIjoiVGVzdCBVc2VyIiwidXBuIjoidGVzdEBleGFtcGxlLmNvbSIsIm9pZCI6InRlc3QtdXNlci1vaWQiLCJ0aWQiOiJ0ZXN0LXRlbmFudC1pZCIsInZlciI6IjIuMCJ9.signature"


@pytest.fixture
def mock_app_token() -> str:
    """Mock app-only access token."""
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhcGk6Ly9tY3Atc2VydmVyIiwiaXNzIjoiaHR0cHM6Ly9sb2dpbi5taWNyb3NvZnRvbmxpbmUuY29tL3Rlc3QtdGVuYW50L3YyLjAiLCJpYXQiOjE3MDU1MDAwMDAsImV4cCI6MTcwNTUwMzU5OSwibmJmIjoxNzA1NTAwMDAwLCJyb2xlcyI6WyJNQ1AuUmVhZC5BbGwiLCJNQ1AuUmVhZFdyaXRlLkFsbCJdLCJhcHBpZCI6InRlc3Qtc2VydmljZS1wcmluY2lwYWwtaWQiLCJpZHR5cCI6ImFwcCIsIm9pZCI6InRlc3Qtc3Atb2lkIiwidGlkIjoidGVzdC10ZW5hbnQtaWQiLCJ2ZXIiOiIyLjAifQ.signature"


@pytest.fixture
def mock_refresh_token() -> str:
    """Mock refresh token."""
    return "0.AXAA_test_refresh_token_value_here"


# ============================================================================
# Mock HTTP Response Fixtures
# ============================================================================


@pytest.fixture
def mock_token_response(mock_user_token: str, mock_refresh_token: str) -> Dict[str, Any]:
    """Mock token response from Entra ID."""
    return {
        "access_token": mock_user_token,
        "refresh_token": mock_refresh_token,
        "expires_in": 3599,
        "token_type": "Bearer",
        "scope": "api://mcp-server/.default",
    }


@pytest.fixture
def mock_app_token_response(mock_app_token: str) -> Dict[str, Any]:
    """Mock app-only token response (no refresh token)."""
    return {
        "access_token": mock_app_token,
        "expires_in": 3599,
        "token_type": "Bearer",
        "ext_expires_in": 3599,
    }


@pytest.fixture
def mock_dcr_response(test_config: Dict[str, str], authorization_endpoint: str, token_endpoint: str) -> Dict[str, Any]:
    """Mock DCR registration response."""
    return {
        "client_id": test_config["client_id"],
        "client_id_issued_at": 1705500000,
        "authorization_endpoint": authorization_endpoint,
        "token_endpoint": token_endpoint,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "redirect_uris": [test_config["redirect_uri"]],
        "token_endpoint_auth_method": "none",
        "require_pkce": True,
    }


@pytest.fixture
def mock_mcp_health_response() -> Dict[str, str]:
    """Mock MCP /health endpoint response."""
    return {"status": "healthy"}


@pytest.fixture
def mock_mcp_me_response_user() -> Dict[str, Any]:
    """Mock MCP /api/me endpoint response for user token."""
    return {
        "token_type": "user",
        "identity": {
            "user_id": "test-user-oid",
            "user_principal": "test@example.com",
            "display_name": "Test User",
            "tenant_id": "test-tenant-id",
        },
        "permissions": {
            "scopes": ["mcp.read", "mcp.write"],
        },
    }


@pytest.fixture
def mock_mcp_me_response_app() -> Dict[str, Any]:
    """Mock MCP /api/me endpoint response for app token."""
    return {
        "token_type": "app_only",
        "identity": {
            "app_id": "test-service-principal-id",
            "app_display_name": "MCP Service Principal",
            "tenant_id": "test-tenant-id",
        },
        "permissions": {
            "roles": ["MCP.Read.All", "MCP.ReadWrite.All"],
        },
    }


# ============================================================================
# Mock HTTP Client Fixtures
# ============================================================================


def create_mock_response(status_code: int, json_data: Dict[str, Any] = None, text: str = None) -> Response:
    """Create a mock httpx.Response."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data if json_data else {}
    mock_response.text = text if text else ""
    return mock_response


@pytest.fixture
def mock_successful_token_response(mock_token_response: Dict[str, Any]) -> Response:
    """Mock successful token exchange response."""
    return create_mock_response(200, mock_token_response)


@pytest.fixture
def mock_successful_app_token_response(mock_app_token_response: Dict[str, Any]) -> Response:
    """Mock successful app-only token response."""
    return create_mock_response(200, mock_app_token_response)


@pytest.fixture
def mock_successful_dcr_response(mock_dcr_response: Dict[str, Any]) -> Response:
    """Mock successful DCR registration response."""
    return create_mock_response(200, mock_dcr_response)


@pytest.fixture
def mock_failed_token_response() -> Response:
    """Mock failed token exchange response."""
    return create_mock_response(
        400,
        {
            "error": "invalid_grant",
            "error_description": "AADSTS70000: The provided authorization code is invalid.",
        },
    )


@pytest.fixture
def mock_successful_health_response(mock_mcp_health_response: Dict[str, str]) -> Response:
    """Mock successful MCP health check response."""
    return create_mock_response(200, mock_mcp_health_response)


@pytest.fixture
def mock_successful_me_response_user(mock_mcp_me_response_user: Dict[str, Any]) -> Response:
    """Mock successful MCP /api/me response for user."""
    return create_mock_response(200, mock_mcp_me_response_user)


@pytest.fixture
def mock_successful_me_response_app(mock_mcp_me_response_app: Dict[str, Any]) -> Response:
    """Mock successful MCP /api/me response for app."""
    return create_mock_response(200, mock_mcp_me_response_app)


@pytest.fixture
def mock_unauthorized_response() -> Response:
    """Mock unauthorized response from MCP API."""
    return create_mock_response(401, {"detail": "Invalid authentication credentials"})


# ============================================================================
# OAuth Flow Fixtures
# ============================================================================


@pytest.fixture
def mock_authorization_code() -> str:
    """Mock OAuth authorization code."""
    return "test-authorization-code-abc123xyz"


@pytest.fixture
def mock_callback_url(test_config: Dict[str, str], mock_authorization_code: str, state_value: str) -> str:
    """Mock OAuth callback URL with code and state."""
    return f"{test_config['redirect_uri']}?code={mock_authorization_code}&state={state_value}"


@pytest.fixture
def mock_error_callback_url(test_config: Dict[str, str]) -> str:
    """Mock OAuth callback URL with error."""
    return f"{test_config['redirect_uri']}?error=access_denied&error_description=User+declined+consent"


# ============================================================================
# Monkeypatch Helpers
# ============================================================================


@pytest.fixture
def mock_webbrowser_open(monkeypatch):
    """Mock webbrowser.open to prevent browser from opening in tests."""
    mock_open = MagicMock()
    monkeypatch.setattr("webbrowser.open", mock_open)
    return mock_open


@pytest.fixture
def mock_time(monkeypatch):
    """Mock time.time() for token expiration testing."""
    mock_time_func = MagicMock(return_value=1705500000)
    monkeypatch.setattr("time.time", mock_time_func)
    return mock_time_func


# ============================================================================
# Environment Variable Fixtures
# ============================================================================


@pytest.fixture
def mock_env_vars(monkeypatch, test_config: Dict[str, str]):
    """Set mock environment variables for client configuration."""
    monkeypatch.setenv("CLIENT_ID", test_config["client_id"])
    monkeypatch.setenv("CLIENT_SECRET", test_config["client_secret"])
    monkeypatch.setenv("TENANT_ID", test_config["tenant_id"])
    monkeypatch.setenv("MCP_SERVER_URL", test_config["mcp_server_url"])
    monkeypatch.setenv("REDIRECT_URI", test_config["redirect_uri"])
    monkeypatch.setenv("SCOPE", test_config["scope"])
    return test_config
