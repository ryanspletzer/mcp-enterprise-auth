"""Unit tests for KeyManager."""

import pytest

from app.crypto.key_manager import KeyManager


@pytest.mark.unit
class TestKeyManager:
    """Test KeyManager functionality."""

    def test_initialization(self):
        """Test key manager initializes with default key."""
        km = KeyManager()

        assert km.current_kid is not None
        assert len(km.keys) == 1
        assert km.current_kid in km.keys

    def test_get_current_signing_key(self):
        """Test getting current signing key."""
        km = KeyManager()

        private_key_pem, kid = km.get_current_signing_key()

        assert isinstance(private_key_pem, bytes)
        assert isinstance(kid, str)
        assert kid == km.current_kid
        assert b"BEGIN PRIVATE KEY" in private_key_pem

    def test_get_jwks(self):
        """Test JWKS generation."""
        km = KeyManager()

        jwks = km.get_jwks()

        assert "keys" in jwks
        assert isinstance(jwks["keys"], list)
        assert len(jwks["keys"]) == 1

        jwk = jwks["keys"][0]
        assert jwk["kty"] == "RSA"
        assert jwk["use"] == "sig"
        assert jwk["alg"] == "RS256"
        assert "kid" in jwk
        assert "n" in jwk  # Modulus
        assert "e" in jwk  # Exponent

    def test_rotate_key(self):
        """Test key rotation."""
        km = KeyManager()

        old_kid = km.current_kid
        new_kid = km.rotate_key()

        assert new_kid != old_kid
        assert km.current_kid == new_kid
        assert len(km.keys) == 2  # Both old and new keys
        assert old_kid in km.keys
        assert new_kid in km.keys

    def test_jwks_after_rotation(self):
        """Test JWKS contains both keys after rotation."""
        km = KeyManager()

        km.rotate_key()
        jwks = km.get_jwks()

        assert len(jwks["keys"]) == 2
