#!/usr/bin/env python3
"""
MCP Public Client - No Credentials (DCR Flow)

This client demonstrates:
1. Dynamic Client Registration (DCR) emulation
2. OAuth Authorization Code flow with PKCE
3. Token acquisition from Entra ID
4. Authenticated MCP API calls

This client does NOT have a pre-configured client_id. It relies on the
MCP server's DCR emulation to detect the client type and return appropriate
credentials.
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

    def do_GET(self):
        """Handle OAuth callback."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.authorization_code = params["code"][0]
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


class MCPPublicClient:
    """MCP Public Client without pre-configured credentials."""

    def __init__(
        self,
        mcp_server_url: str,
        redirect_uri: str = "http://localhost:8080/callback",
        scope: str = "api://mcp-server/.default",
        user_agent: str = "Generic-MCP-Client/1.0",
    ):
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.user_agent = user_agent
        self.client_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.token_endpoint: Optional[str] = None
        self.authorization_endpoint: Optional[str] = None

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        # Generate code_verifier (43-128 chars)
        code_verifier = urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
        code_verifier = code_verifier.rstrip("=")

        # Generate code_challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = urlsafe_b64encode(challenge_bytes).decode("utf-8")
        code_challenge = code_challenge.rstrip("=")

        return code_verifier, code_challenge

    async def register_with_dcr(self) -> dict:
        """Register with MCP server using DCR emulation."""
        logger.info("dcr_registration_starting", mcp_server_url=self.mcp_server_url)

        dcr_request = {
            "redirect_uris": [self.redirect_uri],
            "client_name": "Generic MCP Client (No Creds)",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",  # Public client
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_server_url}/dcr/register",
                json=dcr_request,
                headers={"User-Agent": self.user_agent},
            )

            if response.status_code != 200:
                logger.error(
                    "dcr_registration_failed",
                    status_code=response.status_code,
                    response=response.text,
                )
                raise Exception(f"DCR registration failed: {response.text}")

            dcr_response = response.json()
            logger.info("dcr_registration_successful", client_id=dcr_response.get("client_id"))

            self.client_id = dcr_response["client_id"]
            self.token_endpoint = dcr_response["token_endpoint"]
            self.authorization_endpoint = dcr_response["authorization_endpoint"]

            return dcr_response

    def _start_callback_server(self, timeout: int = 300) -> Optional[str]:
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

        code = OAuthCallbackHandler.authorization_code
        # Reset for next use
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None

        return code

    async def authorize(self) -> str:
        """Perform OAuth Authorization Code flow with PKCE."""
        if not self.client_id or not self.authorization_endpoint:
            raise Exception("Must call register_with_dcr() first")

        logger.info("authorization_flow_starting")

        # Generate PKCE pair
        code_verifier, code_challenge = self._generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        auth_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{self.authorization_endpoint}?{urlencode(auth_params)}"
        logger.info("opening_browser_for_authorization", auth_url=auth_url)

        # Open browser for user authorization
        webbrowser.open(auth_url)

        # Wait for callback
        logger.info("waiting_for_oauth_callback")
        authorization_code = self._start_callback_server()

        logger.info("authorization_code_received")

        # Exchange code for token
        return await self._exchange_code_for_token(authorization_code, code_verifier)

    async def _exchange_code_for_token(
        self, authorization_code: str, code_verifier: str
    ) -> str:
        """Exchange authorization code for access token."""
        logger.info("exchanging_code_for_token")

        token_params = {
            "client_id": self.client_id,
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

            logger.info(
                "token_acquired",
                expires_in=token_response.get("expires_in"),
                token_type=token_response.get("token_type"),
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
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")
    scope = os.getenv("SCOPE", "api://mcp-server/.default")

    logger.info(
        "client_starting",
        mcp_server_url=mcp_server_url,
        redirect_uri=redirect_uri,
        scope=scope,
    )

    # Create client
    client = MCPPublicClient(
        mcp_server_url=mcp_server_url,
        redirect_uri=redirect_uri,
        scope=scope,
    )

    try:
        # Step 1: Register with DCR
        logger.info("=== Step 1: DCR Registration ===")
        dcr_response = await client.register_with_dcr()
        logger.info("dcr_response", response=dcr_response)

        # Step 2: Authorize and get token
        logger.info("=== Step 2: OAuth Authorization ===")
        access_token = await client.authorize()
        logger.info("access_token_acquired", token_length=len(access_token))

        # Step 3: Call MCP API endpoints
        logger.info("=== Step 3: MCP API Calls ===")

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
            client_id=client.client_id,
            token_type=me.get("token_type"),
            identity=me.get("identity", {}).get("user_principal"),
        )

    except Exception as e:
        logger.error("client_error", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
