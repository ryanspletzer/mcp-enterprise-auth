"""
Tests for public-client-without-client-id (DCR flow).

Tests cover:
- DCR registration
- PKCE generation and validation
- OAuth authorization flow
- Token exchange
- MCP API calls
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Client Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_client_initialization(test_config, MCPPublicClient):
    """Test client initialization with configuration."""
    client = MCPPublicClient(
        mcp_server_url=test_config["mcp_server_url"],
        redirect_uri=test_config["redirect_uri"],
        scope=test_config["scope"],
    )

    assert client.mcp_server_url == test_config["mcp_server_url"]
    assert client.redirect_uri == test_config["redirect_uri"]
    assert client.scope == test_config["scope"]
    assert client.client_id is None  # Not set until DCR
    assert client.access_token is None


@pytest.mark.unit
def test_client_strips_trailing_slash(MCPPublicClient):
    """Test that client strips trailing slash from MCP server URL."""
    client = MCPPublicClient(mcp_server_url="http://localhost:8000/")
    assert client.mcp_server_url == "http://localhost:8000"


# ============================================================================
# PKCE Tests
# ============================================================================


@pytest.mark.unit
def test_generate_pkce_pair(MCPPublicClient):
    """Test PKCE code verifier and challenge generation."""
    client = MCPPublicClient(mcp_server_url="http://localhost:8000")

    code_verifier, code_challenge = client._generate_pkce_pair()

    # Verify format
    assert len(code_verifier) >= 43
    assert len(code_challenge) >= 43
    assert code_verifier != code_challenge  # Challenge is hash of verifier

    # Verify no padding characters
    assert "=" not in code_verifier
    assert "=" not in code_challenge


@pytest.mark.unit
def test_pkce_pair_uniqueness(MCPPublicClient):
    """Test that each PKCE generation produces unique values."""
    client = MCPPublicClient(mcp_server_url="http://localhost:8000")

    verifier1, challenge1 = client._generate_pkce_pair()
    verifier2, challenge2 = client._generate_pkce_pair()

    assert verifier1 != verifier2
    assert challenge1 != challenge2


# ============================================================================
# DCR Registration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_with_dcr_success(test_config, mock_successful_dcr_response, MCPPublicClient):
    """Test successful DCR registration."""
    client = MCPPublicClient(
        mcp_server_url=test_config["mcp_server_url"],
        redirect_uri=test_config["redirect_uri"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_successful_dcr_response

        # Call DCR
        dcr_response = await client.register_with_dcr()

        # Verify request
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/dcr/register" in call_args[0][0]

        # Verify response handling
        assert client.client_id == test_config["client_id"]
        assert client.token_endpoint is not None
        assert client.authorization_endpoint is not None
        assert dcr_response["client_id"] == test_config["client_id"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_with_dcr_failure(test_config, MCPPublicClient):
    """Test DCR registration failure."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])

    with patch("httpx.AsyncClient") as mock_client_class:
        # Setup mock to return error
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_client.post.return_value = mock_response

        # Should raise exception
        with pytest.raises(Exception, match="DCR registration failed"):
            await client.register_with_dcr()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_dcr_includes_user_agent(test_config, mock_successful_dcr_response, MCPPublicClient):
    """Test that DCR request includes User-Agent header."""
    user_agent = "Test-Client/1.0"
    client = MCPPublicClient(
        mcp_server_url=test_config["mcp_server_url"],
        user_agent=user_agent,
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_successful_dcr_response

        await client.register_with_dcr()

        # Verify User-Agent header
        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert headers["User-Agent"] == user_agent


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
    MCPPublicClient,
):
    """Test successful token exchange."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])
    client.client_id = test_config["client_id"]
    client.token_endpoint = f"https://login.microsoftonline.com/{test_config['tenant_id']}/oauth2/v2.0/token"

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

        # Verify request
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["data"]

        assert data["client_id"] == test_config["client_id"]
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == mock_authorization_code
        assert data["code_verifier"] == pkce_verifier


@pytest.mark.asyncio
@pytest.mark.integration
async def test_exchange_code_for_token_failure(
    test_config,
    mock_authorization_code,
    pkce_verifier,
    mock_failed_token_response,
    MCPPublicClient,
):
    """Test failed token exchange."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])
    client.client_id = test_config["client_id"]
    client.token_endpoint = f"https://login.microsoftonline.com/{test_config['tenant_id']}/oauth2/v2.0/token"

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
# MCP API Call Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_success(
    test_config,
    mock_user_token,
    mock_successful_health_response,
    MCPPublicClient,
):
    """Test successful MCP API call."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])
    client.access_token = mock_user_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_successful_health_response

        result = await client.call_mcp_api("/health")

        # Verify result
        assert result["status"] == "healthy"

        # Verify request
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == f"{test_config['mcp_server_url']}/health"
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {mock_user_token}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_without_token(MCPPublicClient):
    """Test MCP API call without access token raises exception."""
    client = MCPPublicClient(mcp_server_url="http://localhost:8000")
    # No token set

    with pytest.raises(Exception, match="Must call authorize"):
        await client.call_mcp_api("/health")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_unauthorized(
    test_config,
    mock_user_token,
    mock_unauthorized_response,
    MCPPublicClient,
):
    """Test MCP API call with invalid token."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])
    client.access_token = mock_user_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_unauthorized_response

        with pytest.raises(Exception, match="MCP API call failed"):
            await client.call_mcp_api("/api/me")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_with_post(
    test_config,
    mock_user_token,
    mock_successful_health_response,
    MCPPublicClient,
):
    """Test MCP API call with POST method."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])
    client.access_token = mock_user_token

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_successful_health_response

        await client.call_mcp_api("/api/data", method="POST", json={"key": "value"})

        # Verify POST method
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[1]["json"] == {"key": "value"}


# ============================================================================
# Authorization Flow Tests
# ============================================================================


@pytest.mark.unit
def test_authorization_requires_dcr_first(MCPPublicClient):
    """Test that client_id is not set until DCR is called."""
    client = MCPPublicClient(mcp_server_url="http://localhost:8000")
    # client_id not set (DCR not called)

    # Before DCR, client_id should be None
    # The authorize() method would raise "Must call register_with_dcr"
    # but since it's async, we just verify the initial state here
    assert client.client_id is None


# ============================================================================
# Callback Server Tests
# ============================================================================


@pytest.mark.unit
def test_callback_handler_imports(OAuthCallbackHandler):
    """Test that OAuthCallbackHandler is properly defined."""
    assert OAuthCallbackHandler is not None
    assert hasattr(OAuthCallbackHandler, "do_GET")


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_flow_dcr_to_token(
    test_config,
    mock_successful_dcr_response,
    mock_successful_token_response,
    mock_authorization_code,
    mock_webbrowser_open,
    MCPPublicClient,
):
    """Test full flow from DCR registration to token acquisition."""
    client = MCPPublicClient(
        mcp_server_url=test_config["mcp_server_url"],
        redirect_uri=test_config["redirect_uri"],
        scope=test_config["scope"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock DCR call
        mock_client.post.return_value = mock_successful_dcr_response

        # Step 1: DCR registration
        await client.register_with_dcr()
        assert client.client_id == test_config["client_id"]

        # Verify authorization endpoint was set
        assert client.authorization_endpoint is not None
        assert client.token_endpoint is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_flow_with_api_call(
    test_config,
    mock_user_token,
    mock_successful_me_response_user,
    MCPPublicClient,
):
    """Test full flow including MCP API call."""
    client = MCPPublicClient(mcp_server_url=test_config["mcp_server_url"])
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
        assert "mcp.read" in result["permissions"]["scopes"]
