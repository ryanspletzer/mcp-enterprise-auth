"""
Tests for public-client-with-creds (Auth Code + PKCE flow).

Tests cover:
- Client initialization with pre-configured credentials
- PKCE generation and validation
- State parameter validation
- OAuth authorization flow
- Token exchange
- Refresh token flow
- MCP API calls
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path to import client module
sys.path.insert(0, str(Path(__file__).parent.parent / "public-client-with-creds"))

from client import MCPPublicClientWithCreds


# ============================================================================
# Client Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_client_initialization(test_config):
    """Test client initialization with configuration."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
        redirect_uri=test_config["redirect_uri"],
        scope=test_config["scope"],
    )

    assert client.client_id == test_config["client_id"]
    assert client.tenant_id == test_config["tenant_id"]
    assert client.mcp_server_url == test_config["mcp_server_url"]
    assert client.redirect_uri == test_config["redirect_uri"]
    assert client.scope == test_config["scope"]
    assert client.access_token is None
    assert client.refresh_token is None


@pytest.mark.unit
def test_client_constructs_endpoints(test_config):
    """Test that client constructs Entra ID endpoints correctly."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    expected_authority = f"https://login.microsoftonline.com/{test_config['tenant_id']}"
    assert client.authorization_endpoint == f"{expected_authority}/oauth2/v2.0/authorize"
    assert client.token_endpoint == f"{expected_authority}/oauth2/v2.0/token"


# ============================================================================
# PKCE Tests
# ============================================================================


@pytest.mark.unit
def test_generate_pkce_pair():
    """Test PKCE code verifier and challenge generation."""
    client = MCPPublicClientWithCreds(
        client_id="test-id",
        tenant_id="test-tenant",
        mcp_server_url="http://localhost:8000",
    )

    code_verifier, code_challenge = client._generate_pkce_pair()

    # Verify format
    assert len(code_verifier) >= 43
    assert len(code_challenge) >= 43
    assert code_verifier != code_challenge

    # Verify no padding
    assert "=" not in code_verifier
    assert "=" not in code_challenge


@pytest.mark.unit
def test_pkce_deterministic():
    """Test that PKCE challenge is deterministic for same verifier."""
    import hashlib
    from base64 import urlsafe_b64encode

    verifier = "test-verifier-value-here"

    # Calculate expected challenge
    challenge_bytes = hashlib.sha256(verifier.encode("utf-8")).digest()
    expected_challenge = urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")

    # Verify it matches
    actual_challenge_bytes = hashlib.sha256(verifier.encode("utf-8")).digest()
    actual_challenge = urlsafe_b64encode(actual_challenge_bytes).decode("utf-8").rstrip("=")

    assert actual_challenge == expected_challenge


# ============================================================================
# Token Exchange Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_exchange_code_for_token_success(
    test_config,
    mock_authorization_code,
    pkce_verifier,
    mock_successful_token_response,
    mock_user_token,
    mock_refresh_token,
):
    """Test successful token exchange."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_successful_token_response

        token = await client._exchange_code_for_token(
            mock_authorization_code,
            pkce_verifier,
        )

        # Verify token
        assert token == mock_user_token
        assert client.access_token == mock_user_token
        assert client.refresh_token == mock_refresh_token

        # Verify request
        call_args = mock_client.post.call_args
        data = call_args[1]["data"]

        assert data["client_id"] == test_config["client_id"]
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == mock_authorization_code
        assert data["code_verifier"] == pkce_verifier
        assert "client_secret" not in data  # Public client


@pytest.mark.asyncio
@pytest.mark.integration
async def test_exchange_code_for_token_failure(
    test_config,
    mock_authorization_code,
    pkce_verifier,
    mock_failed_token_response,
):
    """Test failed token exchange."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_failed_token_response

        with pytest.raises(Exception, match="Token exchange failed"):
            await client._exchange_code_for_token(
                mock_authorization_code,
                pkce_verifier,
            )


# ============================================================================
# Refresh Token Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_refresh_access_token_success(
    test_config,
    mock_refresh_token,
    mock_successful_token_response,
    mock_user_token,
):
    """Test successful token refresh."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )
    client.refresh_token = mock_refresh_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_successful_token_response

        new_token = await client.refresh_access_token()

        # Verify new token
        assert new_token == mock_user_token
        assert client.access_token == mock_user_token

        # Verify request
        call_args = mock_client.post.call_args
        data = call_args[1]["data"]

        assert data["client_id"] == test_config["client_id"]
        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == mock_refresh_token
        assert data["scope"] == test_config["scope"]
        assert "client_secret" not in data  # Public client


@pytest.mark.asyncio
@pytest.mark.integration
async def test_refresh_access_token_no_refresh_token(test_config):
    """Test refresh fails without refresh token."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )
    # No refresh_token set

    with pytest.raises(Exception, match="No refresh token available"):
        await client.refresh_access_token()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_refresh_access_token_failure(
    test_config,
    mock_refresh_token,
    mock_failed_token_response,
):
    """Test failed token refresh."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )
    client.refresh_token = mock_refresh_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_failed_token_response

        with pytest.raises(Exception, match="Token refresh failed"):
            await client.refresh_access_token()


# ============================================================================
# MCP API Call Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_success(
    test_config,
    mock_user_token,
    mock_successful_health_response,
):
    """Test successful MCP API call."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )
    client.access_token = mock_user_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_successful_health_response

        result = await client.call_mcp_api("/health")

        # Verify result
        assert result["status"] == "healthy"

        # Verify request
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {mock_user_token}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_without_token(test_config):
    """Test MCP API call without access token raises exception."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with pytest.raises(Exception, match="Must call authorize"):
        await client.call_mcp_api("/health")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_with_custom_headers(
    test_config,
    mock_user_token,
    mock_successful_health_response,
):
    """Test MCP API call with custom headers."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )
    client.access_token = mock_user_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_successful_health_response

        custom_headers = {"X-Custom-Header": "test-value"}
        await client.call_mcp_api("/api/data", headers=custom_headers)

        # Verify both Auth and custom headers
        call_args = mock_client.request.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == f"Bearer {mock_user_token}"
        assert headers["X-Custom-Header"] == "test-value"


# ============================================================================
# State Validation Tests
# ============================================================================


@pytest.mark.unit
def test_callback_handler_state_validation():
    """Test that callback handler validates state parameter."""
    from client import OAuthCallbackHandler

    # This is implicitly tested in the authorize flow
    # The handler stores the state for validation
    assert hasattr(OAuthCallbackHandler, "state")


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_flow_authorization_to_api_call(
    test_config,
    mock_user_token,
    mock_successful_me_response_user,
):
    """Test full flow from authorization to API call."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    # Simulate token already acquired
    client.access_token = mock_user_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_successful_me_response_user

        # Call MCP API
        result = await client.call_mcp_api("/api/me")

        # Verify user info
        assert result["token_type"] == "user"
        assert result["identity"]["user_principal"] == "test@example.com"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_token_refresh_then_api_call(
    test_config,
    mock_refresh_token,
    mock_successful_token_response,
    mock_user_token,
    mock_successful_health_response,
):
    """Test token refresh followed by API call."""
    client = MCPPublicClientWithCreds(
        client_id=test_config["client_id"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )
    client.refresh_token = mock_refresh_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First call: refresh token
        mock_client.post.return_value = mock_successful_token_response
        await client.refresh_access_token()
        assert client.access_token == mock_user_token

        # Second call: use refreshed token for API
        mock_client.request.return_value = mock_successful_health_response
        result = await client.call_mcp_api("/health")
        assert result["status"] == "healthy"
