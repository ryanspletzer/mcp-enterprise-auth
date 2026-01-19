"""Integration tests for OAuth flows."""

import pytest
from fastapi.testclient import TestClient
from jose import jwt


@pytest.mark.integration
class TestAuthorizationCodeFlow:
    """Test authorization code flow with PKCE."""

    def test_authorization_endpoint_renders_login(
        self,
        client: TestClient,
        public_client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
        code_challenge: str,
    ):
        """Test authorization endpoint renders login page."""
        response = client.get(
            "/oauth2/v2.0/authorize",
            params={
                "client_id": public_client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
        )

        assert response.status_code == 200
        assert b"Sign in" in response.content
        assert b"session_id" in response.content

    def test_authorization_without_pkce_fails_for_public_client(
        self,
        client: TestClient,
        public_client_id: str,
        redirect_uri: str,
        scope: str,
    ):
        """Test authorization without PKCE fails for public client."""
        response = client.get(
            "/oauth2/v2.0/authorize",
            params={
                "client_id": public_client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope,
            },
            follow_redirects=False,
        )

        # OAuth 2.0 spec: errors are returned via redirect when redirect_uri is valid
        assert response.status_code == 303
        assert "error=invalid_request" in response.headers.get("location", "")
        assert "PKCE" in response.headers.get("location", "")

    def test_authorization_with_invalid_client(
        self,
        client: TestClient,
        redirect_uri: str,
        scope: str,
    ):
        """Test authorization with unknown client fails."""
        response = client.get(
            "/oauth2/v2.0/authorize",
            params={
                "client_id": "unknown-client",
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope,
            },
        )

        assert response.status_code == 400


@pytest.mark.integration
class TestTokenEndpoint:
    """Test token endpoint with all grant types."""

    def test_client_credentials_grant(
        self,
        client: TestClient,
        service_principal_client_id: str,
        service_principal_client_secret: str,
        scope: str,
        test_settings,
    ):
        """Test client_credentials grant type."""
        response = client.post(
            "/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": service_principal_client_id,
                "client_secret": service_principal_client_secret,
                "scope": scope,
            },
        )

        assert response.status_code == 200
        token_data = response.json()

        assert "access_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == test_settings.ACCESS_TOKEN_TTL

        # No refresh_token for client_credentials
        assert "refresh_token" not in token_data

        # Verify token claims
        claims = jwt.get_unverified_claims(token_data["access_token"])
        assert claims["idtyp"] == "app"
        assert "roles" in claims
        assert isinstance(claims["roles"], list)

    def test_client_credentials_with_invalid_secret(
        self,
        client: TestClient,
        service_principal_client_id: str,
        scope: str,
    ):
        """Test client_credentials with wrong secret fails."""
        response = client.post(
            "/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": service_principal_client_id,
                "client_secret": "wrong-secret",
                "scope": scope,
            },
        )

        assert response.status_code == 400
        error = response.json()
        assert error["detail"]["error"] == "invalid_client"

    def test_unsupported_grant_type(
        self,
        client: TestClient,
        public_client_id: str,
    ):
        """Test unsupported grant type fails."""
        response = client.post(
            "/oauth2/v2.0/token",
            data={
                "grant_type": "password",
                "client_id": public_client_id,
            },
        )

        assert response.status_code == 400
        error = response.json()
        assert error["detail"]["error"] == "unsupported_grant_type"


@pytest.mark.integration
class TestJWKSEndpoint:
    """Test JWKS endpoint."""

    def test_jwks_endpoint(self, client: TestClient):
        """Test JWKS endpoint returns public keys."""
        response = client.get("/discovery/v2.0/keys")

        assert response.status_code == 200
        jwks = response.json()

        assert "keys" in jwks
        assert isinstance(jwks["keys"], list)
        assert len(jwks["keys"]) > 0

        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert "kid" in key
        assert "n" in key
        assert "e" in key


@pytest.mark.integration
class TestOIDCDiscovery:
    """Test OIDC discovery endpoint."""

    def test_openid_configuration(self, client: TestClient, test_settings):
        """Test OIDC discovery metadata."""
        response = client.get("/.well-known/openid-configuration")

        assert response.status_code == 200
        config = response.json()

        assert config["issuer"] == test_settings.issuer
        assert config["authorization_endpoint"] == test_settings.authorization_endpoint
        assert config["token_endpoint"] == test_settings.token_endpoint
        assert config["jwks_uri"] == test_settings.jwks_uri

        assert "authorization_code" in config["grant_types_supported"]
        assert "refresh_token" in config["grant_types_supported"]
        assert "client_credentials" in config["grant_types_supported"]

        assert "S256" in config["code_challenge_methods_supported"]
        assert "plain" in config["code_challenge_methods_supported"]


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "mock-entra-idp"
