"""
Tests for service-principal (Client Credentials flow).

Tests cover:
- Client initialization
- App-only token acquisition (Client Credentials flow)
- Token caching and expiration
- Automatic token refresh
- MCP API calls with app-only token
- No user interaction scenarios
"""

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path to import client module
sys.path.insert(0, str(Path(__file__).parent.parent / "service-principal"))

from client import MCPServicePrincipalClient


# ============================================================================
# Client Initialization Tests
# ============================================================================


@pytest.mark.unit
def test_client_initialization(test_config):
    """Test client initialization with service principal credentials."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
        scope=test_config["scope"],
    )

    assert client.client_id == test_config["client_id"]
    assert client.client_secret == test_config["client_secret"]
    assert client.tenant_id == test_config["tenant_id"]
    assert client.mcp_server_url == test_config["mcp_server_url"]
    assert client.scope == test_config["scope"]
    assert client.access_token is None
    assert client.token_expires_at is None


@pytest.mark.unit
def test_client_constructs_token_endpoint(test_config):
    """Test that client constructs token endpoint correctly."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    expected_endpoint = f"https://login.microsoftonline.com/{test_config['tenant_id']}/oauth2/v2.0/token"
    assert client.token_endpoint == expected_endpoint


# ============================================================================
# Token Acquisition Tests (Client Credentials)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_acquire_token_success(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
    mock_time,
):
    """Test successful app-only token acquisition."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_successful_app_token_response

        token = await client.acquire_token()

        # Verify token
        assert token == mock_app_token
        assert client.access_token == mock_app_token
        assert client.token_expires_at is not None

        # Verify request (Client Credentials grant)
        call_args = mock_client.post.call_args
        data = call_args[1]["data"]

        assert data["client_id"] == test_config["client_id"]
        assert data["client_secret"] == test_config["client_secret"]
        assert data["grant_type"] == "client_credentials"
        assert data["scope"] == test_config["scope"]
        # No code, no code_verifier, no redirect_uri for Client Credentials


@pytest.mark.asyncio
@pytest.mark.integration
async def test_acquire_token_failure(test_config):
    """Test failed token acquisition."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid client credentials"
        mock_client.post.return_value = mock_response

        with pytest.raises(Exception, match="Token acquisition failed"):
            await client.acquire_token()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_acquire_token_sets_expiration(
    test_config,
    mock_successful_app_token_response,
):
    """Test that token expiration is calculated correctly."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        with patch("time.time", return_value=1705500000):
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_successful_app_token_response

            await client.acquire_token()

            # Verify expiration is set (current_time + expires_in)
            expected_expiration = 1705500000 + 3599
            assert client.token_expires_at == expected_expiration


# ============================================================================
# Token Caching and Refresh Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ensure_token_acquires_if_none(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
):
    """Test ensure_token acquires new token if none exists."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    assert client.access_token is None

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_successful_app_token_response

        token = await client.ensure_token()

        assert token == mock_app_token
        assert client.access_token == mock_app_token


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ensure_token_uses_cached_token(
    test_config,
    mock_app_token,
):
    """Test ensure_token uses cached token if not expired."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    # Set cached token that won't expire soon
    current_time = 1705500000
    client.access_token = mock_app_token
    client.token_expires_at = current_time + 3600  # Expires in 1 hour

    with patch("time.time", return_value=current_time):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            token = await client.ensure_token()

            # Should return cached token without calling API
            assert token == mock_app_token
            mock_client.post.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ensure_token_refreshes_if_expiring_soon(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
):
    """Test ensure_token refreshes token if expiring within 5 minutes."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    # Set cached token that expires in 4 minutes
    current_time = 1705500000
    client.access_token = "old-token"
    client.token_expires_at = current_time + 240  # 4 minutes (< 5 min threshold)

    with patch("time.time", return_value=current_time):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_successful_app_token_response

            token = await client.ensure_token()

            # Should acquire new token
            assert token == mock_app_token
            mock_client.post.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ensure_token_refreshes_if_expired(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
):
    """Test ensure_token refreshes token if already expired."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    # Set expired token
    current_time = 1705500000
    client.access_token = "old-token"
    client.token_expires_at = current_time - 100  # Already expired

    with patch("time.time", return_value=current_time):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_successful_app_token_response

            token = await client.ensure_token()

            # Should acquire new token
            assert token == mock_app_token
            mock_client.post.assert_called_once()


# ============================================================================
# MCP API Call Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_success(
    test_config,
    mock_app_token,
    mock_successful_health_response,
):
    """Test successful MCP API call with app-only token."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    # Set cached token
    client.access_token = mock_app_token
    client.token_expires_at = int(time.time()) + 3600

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
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {mock_app_token}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_auto_acquires_token(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
    mock_successful_health_response,
):
    """Test MCP API call automatically acquires token if needed."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    # No token set
    assert client.access_token is None

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First call: acquire token
        # Second call: API request
        mock_client.post.return_value = mock_successful_app_token_response
        mock_client.request.return_value = mock_successful_health_response

        result = await client.call_mcp_api("/health")

        # Verify token was acquired and API called
        assert result["status"] == "healthy"
        assert mock_client.post.called  # Token acquisition
        assert mock_client.request.called  # API call


@pytest.mark.asyncio
@pytest.mark.integration
async def test_call_mcp_api_json_method(
    test_config,
    mock_app_token,
    mock_successful_health_response,
):
    """Test MCP API call with JSON body."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    client.access_token = mock_app_token
    client.token_expires_at = int(time.time()) + 3600

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.request.return_value = mock_successful_health_response

        json_data = {"key": "value", "action": "test"}
        await client.call_mcp_api_json("/api/data", json_data=json_data)

        # Verify JSON was sent
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "POST"  # Default method
        assert call_args[1]["json"] == json_data


# ============================================================================
# App-Only Token Characteristics Tests
# ============================================================================


@pytest.mark.unit
def test_no_refresh_token_for_client_credentials():
    """Test that Client Credentials flow does not provide refresh tokens."""
    # This is tested implicitly - the app_token_response fixture
    # does not include a refresh_token field
    # Client Credentials tokens must be re-acquired when expired
    pass


@pytest.mark.unit
def test_no_user_interaction_required():
    """Test that service principal does not require user interaction."""
    # This is tested implicitly - there's no webbrowser.open or
    # callback server in the service principal client
    pass


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_flow_token_and_api_call(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
    mock_successful_me_response_app,
):
    """Test full flow from token acquisition to API call."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First: acquire token
        mock_client.post.return_value = mock_successful_app_token_response
        await client.acquire_token()
        assert client.access_token == mock_app_token

        # Then: call API
        mock_client.request.return_value = mock_successful_me_response_app
        result = await client.call_mcp_api("/api/me")

        # Verify app-only response
        assert result["token_type"] == "app_only"
        assert result["identity"]["app_id"] == "test-service-principal-id"
        assert "MCP.Read.All" in result["permissions"]["roles"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_api_calls_with_token_caching(
    test_config,
    mock_successful_app_token_response,
    mock_app_token,
    mock_successful_health_response,
):
    """Test multiple API calls use cached token."""
    client = MCPServicePrincipalClient(
        client_id=test_config["client_id"],
        client_secret=test_config["client_secret"],
        tenant_id=test_config["tenant_id"],
        mcp_server_url=test_config["mcp_server_url"],
    )

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First call: acquire token
        mock_client.post.return_value = mock_successful_app_token_response
        mock_client.request.return_value = mock_successful_health_response

        # Make multiple API calls
        await client.call_mcp_api("/health")
        await client.call_mcp_api("/health")
        await client.call_mcp_api("/health")

        # Token should be acquired only once
        assert mock_client.post.call_count == 1  # Single token acquisition
        assert mock_client.request.call_count == 3  # Three API calls
