"""Interactive OAuth flow tests with real Entra ID.

These tests open a visible browser window where the user manually enters
their Entra ID credentials. This validates the complete OAuth flow
end-to-end with a real identity provider.

Run with: ./scripts/run-interactive-tests.sh

Requirements:
- .env file at repository root (created by Setup-EntraIdAppRegistrations.ps1)
- Valid Entra ID user account for sign-in
- Playwright browsers installed (script handles this automatically)
"""

import pytest
from jose import jwt
from playwright.sync_api import Page

from .conftest import (
    AuthorizationResult,
    EntraConfig,
    PKCEPair,
    TokenResult,
)


@pytest.mark.e2e
class TestPublicClientAuthCodePKCE:
    """Test public client authorization code flow with PKCE.

    This is the recommended flow for native apps and SPAs that cannot
    securely store a client secret.
    """

    def test_authorization_code_flow_with_pkce(
        self,
        page: Page,
        entra_config: EntraConfig,
        pkce_pair: PKCEPair,
        oauth_state: str,
        redirect_uri: str,
        build_authorization_url,
        wait_for_callback,
        exchange_code_for_token,
    ):
        """Complete authorization code + PKCE flow with user sign-in.

        Steps:
        1. Build authorization URL with PKCE challenge
        2. Navigate browser to Entra ID login page
        3. USER MANUALLY SIGNS IN (test waits up to 2 minutes)
        4. Capture authorization code from callback
        5. Exchange code for tokens using PKCE verifier
        6. Verify access token contains expected claims
        """
        # Build authorization URL
        auth_url = build_authorization_url(
            client_id=entra_config.generic_client_id,
            redirect_uri=redirect_uri,
            state=oauth_state,
            code_challenge=pkce_pair.challenge,
        )

        print(f"\n{'=' * 60}")
        print("INTERACTIVE SIGN-IN REQUIRED")
        print("=" * 60)
        print(f"\nPlease sign in to Entra ID in the browser window.")
        print(f"Tenant ID: {entra_config.tenant_id}")
        print(f"Client ID: {entra_config.generic_client_id}")
        print(f"\nYou have 2 minutes to complete sign-in.")
        print("=" * 60 + "\n")

        # Navigate to Entra ID login
        page.goto(auth_url)

        # Wait for user to complete sign-in and redirect to callback
        auth_result: AuthorizationResult = wait_for_callback(page, oauth_state)

        print(f"\n{'=' * 60}")
        print("SIGN-IN COMPLETE - Authorization code received")
        print("=" * 60 + "\n")

        # Exchange code for tokens
        token_result: TokenResult = exchange_code_for_token(
            code=auth_result.code,
            redirect_uri=redirect_uri,
            client_id=entra_config.generic_client_id,
            code_verifier=pkce_pair.verifier,
        )

        # Verify we got an access token
        assert token_result.access_token, "No access token received"
        assert token_result.token_type.lower() == "bearer"

        # Decode and verify token claims (without signature verification)
        claims = jwt.get_unverified_claims(token_result.access_token)

        # Verify audience (can be App ID URI or client ID)
        assert claims.get("aud") in entra_config.valid_audiences, (
            f"Expected audience in {entra_config.valid_audiences}, "
            f"got {claims.get('aud')}"
        )

        # Verify issuer contains tenant ID
        assert entra_config.tenant_id in claims.get("iss", ""), (
            f"Issuer should contain tenant ID {entra_config.tenant_id}"
        )

        # Verify tenant ID claim
        assert claims.get("tid") == entra_config.tenant_id, (
            f"Expected tenant ID {entra_config.tenant_id}, got {claims.get('tid')}"
        )

        # Verify this is a user token (has scp claim, not roles)
        assert "scp" in claims, "User token should have 'scp' claim"

        print(f"Access token validated successfully!")
        print(f"  Subject: {claims.get('sub')}")
        print(f"  Username: {claims.get('preferred_username')}")
        print(f"  Scopes: {claims.get('scp')}")
        print(f"  Expires: {claims.get('exp')}")


@pytest.mark.e2e
class TestConfidentialClientAuthCode:
    """Test confidential client authorization code flow.

    Confidential clients can securely store a client secret and use it
    in the token exchange step for additional security.
    """

    def test_authorization_code_flow_with_secret(
        self,
        page: Page,
        entra_config: EntraConfig,
        pkce_pair: PKCEPair,
        oauth_state: str,
        redirect_uri: str,
        build_authorization_url,
        wait_for_callback,
        exchange_code_for_token,
    ):
        """Complete authorization code flow with client secret.

        Uses PKCE as defense-in-depth even though client has a secret.
        """
        # Build authorization URL
        auth_url = build_authorization_url(
            client_id=entra_config.confidential_client_id,
            redirect_uri=redirect_uri,
            state=oauth_state,
            code_challenge=pkce_pair.challenge,
        )

        print(f"\n{'=' * 60}")
        print("INTERACTIVE SIGN-IN REQUIRED (Confidential Client)")
        print("=" * 60)
        print(f"\nPlease sign in to Entra ID in the browser window.")
        print(f"Client ID: {entra_config.confidential_client_id}")
        print(f"\nYou have 2 minutes to complete sign-in.")
        print("=" * 60 + "\n")

        # Navigate to Entra ID login
        page.goto(auth_url)

        # Wait for user to complete sign-in
        auth_result: AuthorizationResult = wait_for_callback(page, oauth_state)

        print("\nAuthorization code received, exchanging for token...")

        # Exchange code for tokens (with client secret)
        token_result: TokenResult = exchange_code_for_token(
            code=auth_result.code,
            redirect_uri=redirect_uri,
            client_id=entra_config.confidential_client_id,
            code_verifier=pkce_pair.verifier,
            client_secret=entra_config.confidential_client_secret,
        )

        # Verify we got an access token
        assert token_result.access_token, "No access token received"

        # Decode and verify token claims
        claims = jwt.get_unverified_claims(token_result.access_token)

        # Verify audience and tenant (audience can be App ID URI or client ID)
        assert claims.get("aud") in entra_config.valid_audiences
        assert claims.get("tid") == entra_config.tenant_id

        print(f"Confidential client token validated!")
        print(f"  Subject: {claims.get('sub')}")
        print(f"  Scopes: {claims.get('scp')}")


@pytest.mark.e2e
class TestServicePrincipalClientCredentials:
    """Test service principal client credentials grant.

    This flow is fully automated (no user interaction) and uses
    application permissions (roles) instead of delegated permissions.
    """

    def test_client_credentials_grant(
        self,
        entra_config: EntraConfig,
        get_client_credentials_token,
    ):
        """Obtain token using client credentials grant.

        This test does NOT require interactive sign-in - it uses
        the service principal's client secret to authenticate directly.
        """
        print(f"\n{'=' * 60}")
        print("CLIENT CREDENTIALS GRANT (Non-Interactive)")
        print("=" * 60)
        print(f"\nObtaining token for service principal...")
        print(f"Client ID: {entra_config.service_principal_client_id}")
        print("=" * 60 + "\n")

        # Get token using client credentials
        token_result: TokenResult = get_client_credentials_token(
            client_id=entra_config.service_principal_client_id,
            client_secret=entra_config.service_principal_client_secret,
        )

        # Verify we got an access token
        assert token_result.access_token, "No access token received"

        # Decode and verify token claims
        claims = jwt.get_unverified_claims(token_result.access_token)

        # Verify audience and tenant (audience can be App ID URI or client ID)
        assert claims.get("aud") in entra_config.valid_audiences, (
            f"Expected audience in {entra_config.valid_audiences}, got {claims.get('aud')}"
        )
        assert claims.get("tid") == entra_config.tenant_id

        # Verify this is an app token (has roles claim, not scp)
        assert "roles" in claims, "App token should have 'roles' claim"
        assert "MCP.ReadWrite.All" in claims.get("roles", []), (
            "Service principal should have MCP.ReadWrite.All role"
        )

        # Verify this is an app-only token (idtyp=app if present, or no scp claim)
        # Note: idtyp claim may not be present in all Entra ID configurations
        if "idtyp" in claims:
            assert claims.get("idtyp") == "app", "Token should be app-only (idtyp=app)"
        else:
            # If idtyp not present, verify it's an app token by absence of scp claim
            assert "scp" not in claims, "App token should not have 'scp' claim"

        print(f"Service principal token validated!")
        print(f"  App ID: {claims.get('appid')}")
        print(f"  Roles: {claims.get('roles')}")
        print(f"  Token type: {claims.get('idtyp')}")


@pytest.mark.e2e
class TestTokenValidation:
    """Tests for token claim validation."""

    def test_access_token_has_required_claims(
        self,
        page: Page,
        entra_config: EntraConfig,
        pkce_pair: PKCEPair,
        oauth_state: str,
        redirect_uri: str,
        build_authorization_url,
        wait_for_callback,
        exchange_code_for_token,
    ):
        """Verify access token contains all required claims for MCP server.

        The MCP server validates these claims:
        - iss (issuer)
        - aud (audience)
        - tid (tenant ID)
        - exp, nbf, iat (temporal claims)
        - scp or roles (permissions)
        """
        auth_url = build_authorization_url(
            client_id=entra_config.generic_client_id,
            redirect_uri=redirect_uri,
            state=oauth_state,
            code_challenge=pkce_pair.challenge,
        )

        print("\nPlease sign in to verify token claims...")

        page.goto(auth_url)
        auth_result = wait_for_callback(page, oauth_state)

        token_result = exchange_code_for_token(
            code=auth_result.code,
            redirect_uri=redirect_uri,
            client_id=entra_config.generic_client_id,
            code_verifier=pkce_pair.verifier,
        )

        claims = jwt.get_unverified_claims(token_result.access_token)

        # Verify all required claims are present
        required_claims = ["iss", "aud", "tid", "exp", "nbf", "iat", "sub"]
        for claim in required_claims:
            assert claim in claims, f"Missing required claim: {claim}"

        # Verify permission claims (user token should have scp)
        assert "scp" in claims, "User token should have 'scp' (scope) claim"

        # Verify temporal claims are valid
        import time

        current_time = int(time.time())
        assert claims["exp"] > current_time, "Token should not be expired"
        assert claims["nbf"] <= current_time, "Token should be valid (nbf in past)"
        assert claims["iat"] <= current_time, "Token iat should be in the past"

        print("\nAll required claims validated:")
        for claim in required_claims + ["scp"]:
            print(f"  {claim}: {claims.get(claim)}")


@pytest.mark.e2e
class TestErrorHandling:
    """Test OAuth error scenarios."""

    def test_cancelled_sign_in(
        self,
        page: Page,
        entra_config: EntraConfig,
        pkce_pair: PKCEPair,
        oauth_state: str,
        redirect_uri: str,
        build_authorization_url,
    ):
        """Test that cancelled sign-in is handled gracefully.

        If the user closes the browser or cancels, the test should
        fail with an appropriate timeout error.
        """
        auth_url = build_authorization_url(
            client_id=entra_config.generic_client_id,
            redirect_uri=redirect_uri,
            state=oauth_state,
            code_challenge=pkce_pair.challenge,
        )

        print("\n" + "=" * 60)
        print("CANCEL TEST - Close the browser or wait 10 seconds")
        print("=" * 60)
        print("\nThis test validates timeout handling.")
        print("You can close the browser window to trigger the timeout.")
        print("=" * 60 + "\n")

        page.goto(auth_url)

        # Wait with short timeout - this should timeout or error
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        with pytest.raises(PlaywrightTimeout):
            page.wait_for_url(f"{redirect_uri}*", timeout=10000)  # 10 second timeout

        print("\nTimeout handled correctly!")
