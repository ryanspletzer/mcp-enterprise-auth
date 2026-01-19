#!/usr/bin/env python3
"""
MCP Confidential Client - Auth Code + PKCE + Client Secret

This client demonstrates:
1. OAuth Authorization Code flow with PKCE
2. Client authentication with client_secret
3. Token acquisition from Entra ID
4. Authenticated MCP API calls

This client is a CONFIDENTIAL client with both client_id and client_secret.
The client_secret provides additional security during token exchange.
"""

import asyncio
import hashlib
import secrets
import webbrowser
from base64 import urlsafe_b64encode
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import structlog

logger = structlog.get_logger()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    authorization_code: Optional[str] = None
    error: Optional[str] = None
    state: Optional[str] = None

    def do_GET(self):
        """Handle OAuth callback."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.authorization_code = params["code"][0]
            OAuthCallbackHandler.state = params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authentication successful!</h1>"
                b"<p>You can close this window and return to the terminal.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            error_desc = params.get("error_description", ["Unknown error"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h1>Authentication failed!</h1>"
                f"<p>Error: {error_desc}</p>"
                f"</body></html>".encode()
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Invalid callback</h1></body></html>")

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class MCPConfidentialClient:
    """MCP Confidential Client with client_id and client_secret."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        mcp_server_url: str,
        redirect_uri: str = "http://localhost:8080/callback",
        scope: str = "api://mcp-server/.default",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

        # Construct Entra ID endpoints
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.authorization_endpoint = f"{authority}/oauth2/v2.0/authorize"
        self.token_endpoint = f"{authority}/oauth2/v2.0/token"

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        # Generate code_verifier (43-128 chars, URL-safe base64)
        code_verifier = urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
        code_verifier = code_verifier.rstrip("=")

        # Generate code_challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = urlsafe_b64encode(challenge_bytes).decode("utf-8")
        code_challenge = code_challenge.rstrip("=")

        return code_verifier, code_challenge

    def _start_callback_server(self, expected_state: str, timeout: int = 300) -> Optional[str]:
        """Start local HTTP server to receive OAuth callback."""
        port = int(urlparse(self.redirect_uri).port or 8080)
        server = HTTPServer(("localhost", port), OAuthCallbackHandler)
        server.timeout = timeout

        logger.info("callback_server_started", port=port, timeout=timeout)

        # Wait for callback
        while OAuthCallbackHandler.authorization_code is None and OAuthCallbackHandler.error is None:
            server.handle_request()

        if OAuthCallbackHandler.error:
            logger.error("oauth_callback_error", error=OAuthCallbackHandler.error)
            raise Exception(f"OAuth error: {OAuthCallbackHandler.error}")

        # Validate state parameter (CSRF protection)
        if OAuthCallbackHandler.state != expected_state:
            logger.error(
                "state_mismatch",
                expected=expected_state,
                received=OAuthCallbackHandler.state,
            )
            raise Exception("State parameter mismatch - possible CSRF attack")

        code = OAuthCallbackHandler.authorization_code

        # Reset for next use
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None
        OAuthCallbackHandler.state = None

        return code

    async def authorize(self) -> str:
        """Perform OAuth Authorization Code flow with PKCE and client authentication."""
        logger.info(
            "authorization_flow_starting",
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            client_type="confidential",
        )

        # Generate PKCE pair (still recommended even with client_secret)
        code_verifier, code_challenge = self._generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        logger.info("pkce_generated", code_challenge_method="S256")

        # Build authorization URL
        auth_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "response_mode": "query",
        }

        auth_url = f"{self.authorization_endpoint}?{urlencode(auth_params)}"
        logger.info("opening_browser_for_authorization")

        # Open browser for user authorization
        webbrowser.open(auth_url)

        # Wait for callback
        logger.info("waiting_for_oauth_callback")
        authorization_code = self._start_callback_server(expected_state=state)

        logger.info("authorization_code_received")

        # Exchange code for token (with client authentication)
        return await self._exchange_code_for_token(authorization_code, code_verifier)

    async def _exchange_code_for_token(
        self, authorization_code: str, code_verifier: str
    ) -> str:
        """Exchange authorization code for access token with client authentication."""
        logger.info("exchanging_code_for_token", auth_method="client_secret_post")

        # Confidential client includes client_secret in token request
        token_params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,  # Client authentication
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data=token_params,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(
                    "token_exchange_failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise Exception(f"Token exchange failed: {response.text}")

            token_response = response.json()
            self.access_token = token_response["access_token"]
            self.refresh_token = token_response.get("refresh_token")

            logger.info(
                "token_acquired",
                expires_in=token_response.get("expires_in"),
                token_type=token_response.get("token_type"),
                has_refresh_token=self.refresh_token is not None,
            )

            return self.access_token

    async def refresh_access_token(self) -> str:
        """Refresh access token using refresh token with client authentication."""
        if not self.refresh_token:
            raise Exception("No refresh token available")

        logger.info("refreshing_access_token", auth_method="client_secret_post")

        token_params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,  # Client authentication required
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": self.scope,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data=token_params,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(
                    "token_refresh_failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise Exception(f"Token refresh failed: {response.text}")

            token_response = response.json()
            self.access_token = token_response["access_token"]
            self.refresh_token = token_response.get("refresh_token", self.refresh_token)

            logger.info(
                "token_refreshed",
                expires_in=token_response.get("expires_in"),
            )

            return self.access_token

    async def call_mcp_api(self, endpoint: str, method: str = "GET", **kwargs) -> dict:
        """Make authenticated call to MCP API."""
        if not self.access_token:
            raise Exception("Must call authorize() first to get access token")

        url = f"{self.mcp_server_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
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


async def main():
    """Main client flow."""
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
    redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")
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
        "client_starting",
        client_id=client_id,
        tenant_id=tenant_id,
        mcp_server_url=mcp_server_url,
        redirect_uri=redirect_uri,
        scope=scope,
        client_type="confidential",
    )

    # Create client
    client = MCPConfidentialClient(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        mcp_server_url=mcp_server_url,
        redirect_uri=redirect_uri,
        scope=scope,
    )

    try:
        # Step 1: Authorize and get token
        logger.info("=== Step 1: OAuth Authorization ===")
        access_token = await client.authorize()
        logger.info("access_token_acquired", token_length=len(access_token))

        # Step 2: Call MCP API endpoints
        logger.info("=== Step 2: MCP API Calls ===")

        # Health check (no auth required)
        health = await client.call_mcp_api("/health")
        logger.info("health_check", result=health)

        # Get current user info
        me = await client.call_mcp_api("/api/me")
        logger.info("current_user", result=me)

        # Success!
        logger.info("=== Client Flow Complete ===")
        logger.info(
            "summary",
            token_type=me.get("token_type"),
            identity=me.get("identity", {}).get("user_principal"),
            has_refresh_token=client.refresh_token is not None,
        )

    except Exception as e:
        logger.error("client_error", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
