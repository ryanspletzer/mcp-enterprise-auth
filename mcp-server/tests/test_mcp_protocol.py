"""
Tests for MCP Protocol Implementation.

Tests cover:
- Initialize handshake
- Tools listing and calling
- Resources listing and reading
- Prompts listing and getting
- Error handling
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.mcp.models import MCP_PROTOCOL_VERSION


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(valid_user_token):
    """Headers with valid authentication token."""
    return {"Authorization": f"Bearer {valid_user_token}"}


# ============================================================================
# Initialize Tests
# ============================================================================


@pytest.mark.mcp
@pytest.mark.integration
def test_initialize_success(client, auth_headers):
    """Test successful MCP initialization."""
    request_data = {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            "roots": {},
            "sampling": {},
        },
        "clientInfo": {
            "name": "Test Client",
            "version": "1.0.0",
        },
    }

    response = client.post("/mcp/initialize", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["protocolVersion"] == MCP_PROTOCOL_VERSION
    assert "capabilities" in data
    assert "serverInfo" in data
    assert data["serverInfo"]["name"] == "MCP Server with Enterprise Auth"
    assert "tools" in data["capabilities"]
    assert "resources" in data["capabilities"]
    assert "prompts" in data["capabilities"]


@pytest.mark.mcp
@pytest.mark.integration
def test_initialize_without_auth(client):
    """Test initialize without authentication fails."""
    request_data = {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "Test", "version": "1.0"},
    }

    response = client.post("/mcp/initialize", json=request_data)

    assert response.status_code == 401  # Unauthorized


@pytest.mark.mcp
@pytest.mark.integration
def test_initialize_different_protocol_version(client, auth_headers):
    """Test initialize with different protocol version (should still work)."""
    request_data = {
        "protocolVersion": "2023-01-01",  # Different version
        "capabilities": {},
        "clientInfo": {"name": "Test", "version": "1.0"},
    }

    response = client.post("/mcp/initialize", json=request_data, headers=auth_headers)

    # Should still succeed but return our supported version
    assert response.status_code == 200
    data = response.json()
    assert data["protocolVersion"] == MCP_PROTOCOL_VERSION


# ============================================================================
# Tools Tests
# ============================================================================


@pytest.mark.mcp
@pytest.mark.integration
def test_tools_list_success(client, auth_headers):
    """Test listing tools."""
    response = client.post("/mcp/tools/list", json={}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "tools" in data
    assert isinstance(data["tools"], list)
    assert len(data["tools"]) > 0

    # Check tool structure
    tool = data["tools"][0]
    assert "name" in tool
    assert "description" in tool
    assert "inputSchema" in tool


@pytest.mark.mcp
@pytest.mark.integration
def test_tools_list_contains_expected_tools(client, auth_headers):
    """Test that tools list contains expected built-in tools."""
    response = client.post("/mcp/tools/list", json={}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    tool_names = [tool["name"] for tool in data["tools"]]

    # Check for expected tools
    assert "get_weather" in tool_names
    assert "calculate" in tool_names
    assert "echo" in tool_names
    assert "get_current_time" in tool_names
    assert "generate_uuid" in tool_names
    assert "random_number" in tool_names


@pytest.mark.mcp
@pytest.mark.integration
def test_tool_call_get_weather(client, auth_headers):
    """Test calling get_weather tool."""
    request_data = {
        "name": "get_weather",
        "arguments": {
            "location": "San Francisco",
            "units": "fahrenheit",
        },
    }

    response = client.post("/mcp/tools/call", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "content" in data
    assert len(data["content"]) > 0
    assert data["content"][0]["type"] == "text"
    assert "San Francisco" in data["content"][0]["text"]
    assert data["isError"] is False


@pytest.mark.mcp
@pytest.mark.integration
def test_tool_call_calculate(client, auth_headers):
    """Test calling calculate tool."""
    request_data = {
        "name": "calculate",
        "arguments": {
            "expression": "2 + 2",
        },
    }

    response = client.post("/mcp/tools/call", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["isError"] is False
    assert "4" in data["content"][0]["text"]


@pytest.mark.mcp
@pytest.mark.integration
def test_tool_call_echo(client, auth_headers):
    """Test calling echo tool."""
    request_data = {
        "name": "echo",
        "arguments": {
            "message": "Hello, MCP!",
            "repeat": 2,
        },
    }

    response = client.post("/mcp/tools/call", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["isError"] is False
    text = data["content"][0]["text"]
    assert text.count("Hello, MCP!") == 2


@pytest.mark.mcp
@pytest.mark.integration
def test_tool_call_unknown_tool(client, auth_headers):
    """Test calling unknown tool."""
    request_data = {
        "name": "unknown_tool",
        "arguments": {},
    }

    response = client.post("/mcp/tools/call", json=request_data, headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.mcp
@pytest.mark.integration
def test_tool_call_invalid_arguments(client, auth_headers):
    """Test calling tool with invalid arguments."""
    request_data = {
        "name": "calculate",
        "arguments": {
            "expression": "invalid expression {{{{",
        },
    }

    response = client.post("/mcp/tools/call", json=request_data, headers=auth_headers)

    assert response.status_code == 200  # Tool returns error in response
    data = response.json()
    assert data["isError"] is True


# ============================================================================
# Resources Tests
# ============================================================================


@pytest.mark.mcp
@pytest.mark.integration
def test_resources_list_success(client, auth_headers):
    """Test listing resources."""
    response = client.post("/mcp/resources/list", json={}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "resources" in data
    assert isinstance(data["resources"], list)
    assert len(data["resources"]) > 0

    # Check resource structure
    resource = data["resources"][0]
    assert "uri" in resource
    assert "name" in resource
    assert "mimeType" in resource


@pytest.mark.mcp
@pytest.mark.integration
def test_resources_list_contains_expected_resources(client, auth_headers):
    """Test that resources list contains expected resources."""
    response = client.post("/mcp/resources/list", json={}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    resource_uris = [resource["uri"] for resource in data["resources"]]

    # Check for expected resources
    assert "resource://documents/readme" in resource_uris
    assert "resource://documents/api-docs" in resource_uris
    assert "resource://config/server-info" in resource_uris


@pytest.mark.mcp
@pytest.mark.integration
def test_resource_read_success(client, auth_headers):
    """Test reading a resource."""
    request_data = {
        "uri": "resource://documents/readme",
    }

    response = client.post("/mcp/resources/read", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "contents" in data
    assert len(data["contents"]) > 0
    content = data["contents"][0]
    assert content["uri"] == "resource://documents/readme"
    assert content["mimeType"] == "text/markdown"
    assert "text" in content
    assert len(content["text"]) > 0


@pytest.mark.mcp
@pytest.mark.integration
def test_resource_read_json_resource(client, auth_headers):
    """Test reading a JSON resource."""
    request_data = {
        "uri": "resource://config/server-info",
    }

    response = client.post("/mcp/resources/read", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    content = data["contents"][0]
    assert content["mimeType"] == "application/json"
    assert "authentication" in content["text"]  # JSON content as text


@pytest.mark.mcp
@pytest.mark.integration
def test_resource_read_unknown_resource(client, auth_headers):
    """Test reading unknown resource."""
    request_data = {
        "uri": "resource://unknown/resource",
    }

    response = client.post("/mcp/resources/read", json=request_data, headers=auth_headers)

    assert response.status_code == 404


# ============================================================================
# Prompts Tests
# ============================================================================


@pytest.mark.mcp
@pytest.mark.integration
def test_prompts_list_success(client, auth_headers):
    """Test listing prompts."""
    response = client.post("/mcp/prompts/list", json={}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "prompts" in data
    assert isinstance(data["prompts"], list)
    assert len(data["prompts"]) > 0

    # Check prompt structure
    prompt = data["prompts"][0]
    assert "name" in prompt
    assert "description" in prompt
    assert "arguments" in prompt


@pytest.mark.mcp
@pytest.mark.integration
def test_prompts_list_contains_expected_prompts(client, auth_headers):
    """Test that prompts list contains expected prompts."""
    response = client.post("/mcp/prompts/list", json={}, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    prompt_names = [prompt["name"] for prompt in data["prompts"]]

    # Check for expected prompts
    assert "greeting" in prompt_names
    assert "weather_query" in prompt_names
    assert "code_review" in prompt_names
    assert "summarize" in prompt_names


@pytest.mark.mcp
@pytest.mark.integration
def test_prompt_get_greeting(client, auth_headers):
    """Test getting greeting prompt."""
    request_data = {
        "name": "greeting",
        "arguments": {
            "name": "Alice",
            "time_of_day": "morning",
        },
    }

    response = client.post("/mcp/prompts/get", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "messages" in data
    assert len(data["messages"]) > 0
    # Check that the name appears in the prompt
    message_text = str(data["messages"])
    assert "Alice" in message_text


@pytest.mark.mcp
@pytest.mark.integration
def test_prompt_get_weather_query(client, auth_headers):
    """Test getting weather query prompt."""
    request_data = {
        "name": "weather_query",
        "arguments": {
            "location": "Tokyo",
            "detail_level": "detailed",
        },
    }

    response = client.post("/mcp/prompts/get", json=request_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "messages" in data
    message_text = str(data["messages"])
    assert "Tokyo" in message_text


@pytest.mark.mcp
@pytest.mark.integration
def test_prompt_get_unknown_prompt(client, auth_headers):
    """Test getting unknown prompt."""
    request_data = {
        "name": "unknown_prompt",
        "arguments": {},
    }

    response = client.post("/mcp/prompts/get", json=request_data, headers=auth_headers)

    assert response.status_code == 404


# ============================================================================
# MCP Health Check Tests
# ============================================================================


@pytest.mark.mcp
@pytest.mark.integration
def test_mcp_health_check():
    """Test MCP health check endpoint (no auth required)."""
    # Using client without auth
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/mcp/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["protocol_version"] == MCP_PROTOCOL_VERSION
        assert "tools_count" in data
        assert "resources_count" in data
        assert "prompts_count" in data
        assert data["tools_count"] > 0
        assert data["resources_count"] > 0
        assert data["prompts_count"] > 0


# ============================================================================
# End-to-End Flow Tests
# ============================================================================


@pytest.mark.mcp
@pytest.mark.integration
def test_complete_mcp_flow(client, auth_headers):
    """Test complete MCP flow: initialize, list, call."""
    # Step 1: Initialize
    init_response = client.post(
        "/mcp/initialize",
        json={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "Test", "version": "1.0"},
        },
        headers=auth_headers,
    )
    assert init_response.status_code == 200

    # Step 2: List tools
    tools_response = client.post("/mcp/tools/list", json={}, headers=auth_headers)
    assert tools_response.status_code == 200
    tools = tools_response.json()["tools"]
    assert len(tools) > 0

    # Step 3: Call a tool
    call_response = client.post(
        "/mcp/tools/call",
        json={"name": "echo", "arguments": {"message": "test"}},
        headers=auth_headers,
    )
    assert call_response.status_code == 200
    assert call_response.json()["isError"] is False

    # Step 4: List resources
    resources_response = client.post("/mcp/resources/list", json={}, headers=auth_headers)
    assert resources_response.status_code == 200
    resources = resources_response.json()["resources"]
    assert len(resources) > 0

    # Step 5: Read a resource
    read_response = client.post(
        "/mcp/resources/read",
        json={"uri": resources[0]["uri"]},
        headers=auth_headers,
    )
    assert read_response.status_code == 200

    # Step 6: List prompts
    prompts_response = client.post("/mcp/prompts/list", json={}, headers=auth_headers)
    assert prompts_response.status_code == 200
    prompts = prompts_response.json()["prompts"]
    assert len(prompts) > 0

    # Step 7: Get a prompt
    get_prompt_response = client.post(
        "/mcp/prompts/get",
        json={"name": prompts[0]["name"], "arguments": {}},
        headers=auth_headers,
    )
    assert get_prompt_response.status_code == 200
