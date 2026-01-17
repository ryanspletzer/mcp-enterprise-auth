#!/usr/bin/env python3
"""
MCP Service Principal Client - Client Credentials Flow

This client demonstrates:
1. OAuth Client Credentials flow (no user interaction)
2. Service principal authentication
3. App-only token acquisition
4. Authenticated MCP API calls

This client is a SERVICE PRINCIPAL that authenticates as itself (not on behalf of a user).
It uses the Client Credentials grant type for machine-to-machine communication.
"""

import asyncio
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()


class MCPServicePrincipalClient:
    """MCP Service Principal Client using Client Credentials flow."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        mcp_server_url: str,
        scope: str = "api://mcp-server/.default",
    ):
        """
        Initialize service principal client.

        Args:
            client_id: Application (client) ID from Entra ID
            client_secret: Client secret from Entra ID
            tenant_id: Directory (tenant) ID from Entra ID
            mcp_server_url: MCP server base URL
            scope: OAuth scope (use .default for all configured permissions)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.scope = scope
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[int] = None

        # Construct Entra ID token endpoint
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.token_endpoint = f"{authority}/oauth2/v2.0/token"

    async def acquire_token(self) -> str:
        """
        Acquire app-only access token using Client Credentials flow.

        Returns:
            Access token string

        Raises:
            Exception: If token acquisition fails
        """
        logger.info(
            "acquiring_app_only_token",
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            grant_type="client_credentials",
        )

        token_params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "grant_type": "client_credentials",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data=token_params,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(
                    "token_acquisition_failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise Exception(f"Token acquisition failed: {response.text}")

            token_response = response.json()
            self.access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 3599)

            # Calculate expiration time
            import time
            self.token_expires_at = int(time.time()) + expires_in

            logger.info(
                "app_only_token_acquired",
                expires_in=expires_in,
                token_type=token_response.get("token_type"),
                scope=token_response.get("scope"),
            )

            return self.access_token

    async def ensure_token(self) -> str:
        """
        Ensure we have a valid access token, acquiring new one if needed.

        Returns:
            Valid access token
        """
        import time

        # Check if we need a new token
        if not self.access_token or not self.token_expires_at:
            logger.info("no_token_acquiring_new")
            return await self.acquire_token()

        # Check if token is expired or will expire soon (5 min buffer)
        time_until_expiry = self.token_expires_at - int(time.time())
        if time_until_expiry < 300:  # 5 minutes
            logger.info(
                "token_expiring_soon_acquiring_new",
                time_until_expiry=time_until_expiry,
            )
            return await self.acquire_token()

        logger.debug("using_cached_token", time_until_expiry=time_until_expiry)
        return self.access_token

    async def call_mcp_api(self, endpoint: str, method: str = "GET", **kwargs) -> dict:
        """
        Make authenticated call to MCP API.

        Args:
            endpoint: API endpoint path (e.g., "/api/me")
            method: HTTP method (default: GET)
            **kwargs: Additional httpx request parameters

        Returns:
            JSON response from API

        Raises:
            Exception: If API call fails
        """
        # Ensure we have a valid token
        token = await self.ensure_token()

        url = f"{self.mcp_server_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            **kwargs.pop("headers", {}),
        }

        logger.info("calling_mcp_api", method=method, endpoint=endpoint)

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)

            if response.status_code >= 400:
                logger.error(
                    "mcp_api_call_failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise Exception(f"MCP API call failed: {response.text}")

            logger.info("mcp_api_call_successful", status_code=response.status_code)
            return response.json()

    async def call_mcp_api_json(
        self, endpoint: str, method: str = "POST", json_data: dict = None, **kwargs
    ) -> dict:
        """
        Make authenticated call to MCP API with JSON body.

        Args:
            endpoint: API endpoint path
            method: HTTP method (default: POST)
            json_data: JSON data to send
            **kwargs: Additional httpx request parameters

        Returns:
            JSON response from API
        """
        return await self.call_mcp_api(endpoint, method=method, json=json_data, **kwargs)


async def main():
    """Main service principal flow."""
    import os

    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )

    # Configuration from environment
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    tenant_id = os.getenv("TENANT_ID")
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    scope = os.getenv("SCOPE", "api://mcp-server/.default")

    if not client_id or not client_secret or not tenant_id:
        logger.error(
            "missing_required_config",
            client_id=bool(client_id),
            client_secret=bool(client_secret),
            tenant_id=bool(tenant_id),
        )
        raise Exception("CLIENT_ID, CLIENT_SECRET, and TENANT_ID are required")

    logger.info(
        "service_principal_starting",
        client_id=client_id,
        tenant_id=tenant_id,
        mcp_server_url=mcp_server_url,
        scope=scope,
        flow_type="client_credentials",
    )

    # Create client
    client = MCPServicePrincipalClient(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        mcp_server_url=mcp_server_url,
        scope=scope,
    )

    try:
        # Step 1: Acquire app-only token
        logger.info("=== Step 1: Acquire App-Only Token ===")
        access_token = await client.acquire_token()
        logger.info("access_token_acquired", token_length=len(access_token))

        # Step 2: Call MCP API endpoints
        logger.info("=== Step 2: MCP API Calls ===")

        # Health check (no auth required)
        health = await client.call_mcp_api("/health")
        logger.info("health_check", result=health)

        # Get service principal info
        me = await client.call_mcp_api("/api/me")
        logger.info("service_principal_info", result=me)

        # Step 3: Demonstrate automatic token refresh
        logger.info("=== Step 3: Demonstrate Token Management ===")

        # Call API again - should use cached token
        me2 = await client.call_mcp_api("/api/me")
        logger.info("second_api_call_cached_token", result=me2)

        # Success!
        logger.info("=== Service Principal Flow Complete ===")
        logger.info(
            "summary",
            token_type=me.get("token_type"),
            identity=me.get("identity", {}).get("app_id"),
            roles=me.get("permissions", {}).get("roles", []),
        )

    except Exception as e:
        logger.error("service_principal_error", error=str(e), exc_info=True)
        raise


async def run_automated_task():
    """Example: Automated task using service principal."""
    import os

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ]
    )

    logger.info("automated_task_starting")

    # Initialize client
    client = MCPServicePrincipalClient(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        tenant_id=os.getenv("TENANT_ID"),
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8000"),
    )

    # Perform automated operations
    try:
        # Example: Call MCP API endpoints without user interaction
        health = await client.call_mcp_api("/health")
        logger.info("health_check_passed", status=health.get("status"))

        # Example: Process data
        me = await client.call_mcp_api("/api/me")
        app_id = me.get("identity", {}).get("app_id")
        logger.info("authenticated_as_service_principal", app_id=app_id)

        logger.info("automated_task_completed_successfully")

    except Exception as e:
        logger.error("automated_task_failed", error=str(e))
        raise


if __name__ == "__main__":
    # Run main interactive flow
    asyncio.run(main())

    # Or run automated task
    # asyncio.run(run_automated_task())
