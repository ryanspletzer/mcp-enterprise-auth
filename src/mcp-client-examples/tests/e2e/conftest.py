"""Playwright fixtures for interactive OAuth testing with real Entra ID.

These fixtures provide browser automation for OAuth flows where users
manually enter their credentials in a visible browser window.
"""

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Generator
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


@dataclass
class EntraConfig:
    """Entra ID configuration loaded from environment."""

    tenant_id: str
    authority: str
    mcp_server_app_id: str
    generic_client_id: str
    confidential_client_id: str
    confidential_client_secret: str
    service_principal_client_id: str
    service_principal_client_secret: str

    @property
    def authorize_endpoint(self) -> str:
        """OAuth authorization endpoint."""
        return f"{self.authority}/oauth2/v2.0/authorize"

    @property
    def token_endpoint(self) -> str:
        """OAuth token endpoint."""
        return f"{self.authority}/oauth2/v2.0/token"

    @property
    def default_scope(self) -> str:
        """Default scope for MCP server access."""
        return f"{self.mcp_server_app_id}/.default"

    @property
    def user_scopes(self) -> str:
        """User scopes for delegated access."""
        return f"{self.mcp_server_app_id}/mcp.read {self.mcp_server_app_id}/mcp.write"


@dataclass
class PKCEPair:
    """PKCE code verifier and challenge pair."""

    verifier: str
    challenge: str
    method: str = "S256"


def generate_pkce_pair() -> PKCEPair:
    """Generate a PKCE code verifier and challenge.

    Returns:
        PKCEPair with verifier and S256 challenge.
    """
    # Generate 32 random bytes (256 bits) for code verifier
    verifier_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(verifier_bytes).decode("ascii").rstrip("=")

    # Create S256 challenge: BASE64URL(SHA256(verifier))
    challenge_bytes = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).decode("ascii").rstrip("=")

    return PKCEPair(verifier=verifier, challenge=challenge)


@dataclass
class AuthorizationResult:
    """Result of an authorization flow."""

    code: str
    state: str
    redirect_uri: str


@dataclass
class TokenResult:
    """Result of a token exchange."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str
    id_token: str | None = None
    refresh_token: str | None = None


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def entra_config() -> EntraConfig:
    """Load Entra ID configuration from environment variables.

    Requires the following environment variables (set by Setup-EntraIdAppRegistrations.ps1):
    - ENTRA_TENANT_ID
    - ENTRA_AUTHORITY
    - MCP_SERVER_APP_ID
    - GENERIC_CLIENT_ID
    - CONFIDENTIAL_CLIENT_ID
    - CONFIDENTIAL_CLIENT_SECRET
    - SERVICE_PRINCIPAL_CLIENT_ID
    - SERVICE_PRINCIPAL_CLIENT_SECRET
    """

    def get_required_env(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            pytest.skip(
                f"Missing required environment variable: {name}. "
                "Run Setup-EntraIdAppRegistrations.ps1 to generate .env file."
            )
        return value

    return EntraConfig(
        tenant_id=get_required_env("ENTRA_TENANT_ID"),
        authority=get_required_env("ENTRA_AUTHORITY"),
        mcp_server_app_id=get_required_env("MCP_SERVER_APP_ID"),
        generic_client_id=get_required_env("GENERIC_CLIENT_ID"),
        confidential_client_id=get_required_env("CONFIDENTIAL_CLIENT_ID"),
        confidential_client_secret=get_required_env("CONFIDENTIAL_CLIENT_SECRET"),
        service_principal_client_id=get_required_env("SERVICE_PRINCIPAL_CLIENT_ID"),
        service_principal_client_secret=get_required_env(
            "SERVICE_PRINCIPAL_CLIENT_SECRET"
        ),
    )


# =============================================================================
# Browser Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for interactive testing.

    Uses headless=False so the user can see and interact with the login page.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100,  # Slow down for visibility
        )
        yield browser
        browser.close()


@pytest.fixture
def browser_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a fresh browser context for each test.

    Each context is isolated (separate cookies, storage, etc.).
    """
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
    )
    yield context
    context.close()


@pytest.fixture
def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """Create a new page for each test."""
    page = browser_context.new_page()
    yield page
    page.close()


# =============================================================================
# OAuth Helper Fixtures
# =============================================================================


@pytest.fixture
def pkce_pair() -> PKCEPair:
    """Generate a fresh PKCE pair for each test."""
    return generate_pkce_pair()


@pytest.fixture
def oauth_state() -> str:
    """Generate a random state parameter for CSRF protection."""
    return secrets.token_urlsafe(32)


@pytest.fixture
def redirect_uri() -> str:
    """Default redirect URI for testing."""
    return "http://localhost:8080/callback"


# =============================================================================
# Token Exchange Helpers
# =============================================================================


@pytest.fixture
def exchange_code_for_token(entra_config: EntraConfig):
    """Factory fixture to exchange authorization code for tokens.

    Returns a function that can be called with the authorization code
    and related parameters.
    """

    def _exchange(
        code: str,
        redirect_uri: str,
        client_id: str,
        code_verifier: str | None = None,
        client_secret: str | None = None,
        scope: str | None = None,
    ) -> TokenResult:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback.
            redirect_uri: Redirect URI used in authorization request.
            client_id: Client ID of the application.
            code_verifier: PKCE code verifier (for public clients).
            client_secret: Client secret (for confidential clients).
            scope: Requested scope (defaults to .default).

        Returns:
            TokenResult with access token and related data.
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": scope or entra_config.default_scope,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        if client_secret:
            data["client_secret"] = client_secret

        with httpx.Client() as client:
            response = client.post(
                entra_config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_detail = response.json() if response.content else {}
                raise ValueError(
                    f"Token exchange failed: {response.status_code} - {error_detail}"
                )

            token_data = response.json()
            return TokenResult(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                scope=token_data.get("scope", ""),
                id_token=token_data.get("id_token"),
                refresh_token=token_data.get("refresh_token"),
            )

    return _exchange


@pytest.fixture
def get_client_credentials_token(entra_config: EntraConfig):
    """Factory fixture to obtain tokens via client credentials grant.

    Returns a function that can be called with client credentials.
    """

    def _get_token(
        client_id: str,
        client_secret: str,
        scope: str | None = None,
    ) -> TokenResult:
        """Get access token using client credentials grant.

        Args:
            client_id: Application (client) ID.
            client_secret: Client secret.
            scope: Requested scope (defaults to .default).

        Returns:
            TokenResult with access token.
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope or entra_config.default_scope,
        }

        with httpx.Client() as client:
            response = client.post(
                entra_config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                error_detail = response.json() if response.content else {}
                raise ValueError(
                    f"Client credentials grant failed: {response.status_code} - {error_detail}"
                )

            token_data = response.json()
            return TokenResult(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                scope=token_data.get("scope", ""),
            )

    return _get_token


# =============================================================================
# Authorization URL Builder
# =============================================================================


@pytest.fixture
def build_authorization_url(entra_config: EntraConfig):
    """Factory fixture to build authorization URLs.

    Returns a function that constructs the full authorization URL.
    """

    def _build(
        client_id: str,
        redirect_uri: str,
        state: str,
        code_challenge: str | None = None,
        scope: str | None = None,
        prompt: str = "select_account",
    ) -> str:
        """Build OAuth authorization URL.

        Args:
            client_id: Application (client) ID.
            redirect_uri: Redirect URI for callback.
            state: Random state for CSRF protection.
            code_challenge: PKCE code challenge (for public clients).
            scope: Requested scope (defaults to user scopes).
            prompt: Login prompt behavior.

        Returns:
            Full authorization URL.
        """
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": scope or entra_config.user_scopes,
            "state": state,
            "prompt": prompt,
        }

        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        return f"{entra_config.authorize_endpoint}?{urlencode(params)}"

    return _build


# =============================================================================
# Callback Handler
# =============================================================================


@pytest.fixture
def wait_for_callback(redirect_uri: str):
    """Factory fixture to wait for OAuth callback and extract code.

    Returns a function that waits for the page to navigate to the callback URL.
    """

    def _wait(page: Page, expected_state: str, timeout: int = 120000) -> AuthorizationResult:
        """Wait for OAuth callback and extract authorization code.

        Args:
            page: Playwright page instance.
            expected_state: Expected state parameter for CSRF validation.
            timeout: Maximum wait time in milliseconds (default: 2 minutes).

        Returns:
            AuthorizationResult with code and state.

        Raises:
            ValueError: If state mismatch or error in callback.
        """
        # Wait for redirect to callback URL
        page.wait_for_url(f"{redirect_uri}*", timeout=timeout)

        # Parse callback URL
        callback_url = page.url
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        # Check for errors
        if "error" in params:
            error = params["error"][0]
            error_description = params.get("error_description", ["Unknown error"])[0]
            raise ValueError(f"OAuth error: {error} - {error_description}")

        # Validate state
        received_state = params.get("state", [None])[0]
        if received_state != expected_state:
            raise ValueError(
                f"State mismatch - CSRF attack detected. "
                f"Expected: {expected_state}, Got: {received_state}"
            )

        # Extract authorization code
        if "code" not in params:
            raise ValueError("No authorization code in callback")

        return AuthorizationResult(
            code=params["code"][0],
            state=received_state,
            redirect_uri=redirect_uri,
        )

    return _wait
