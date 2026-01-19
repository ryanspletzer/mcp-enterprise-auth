"""Unit tests for PKCE utilities."""

import pytest

from app.utils.pkce import (
    generate_code_challenge,
    generate_code_verifier,
    validate_code_challenge_method,
    verify_code_challenge,
)


@pytest.mark.unit
class TestPKCE:
    """Test PKCE utilities."""

    def test_validate_code_challenge_method(self):
        """Test code challenge method validation."""
        assert validate_code_challenge_method("S256") is True
        assert validate_code_challenge_method("plain") is True
        assert validate_code_challenge_method("invalid") is False
        assert validate_code_challenge_method("sha256") is False

    def test_generate_code_verifier(self):
        """Test code verifier generation."""
        verifier = generate_code_verifier()

        assert isinstance(verifier, str)
        assert len(verifier) == 43  # Default length
        # Should be URL-safe base64
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in verifier)

    def test_generate_code_verifier_custom_length(self):
        """Test code verifier generation with custom length."""
        verifier = generate_code_verifier(length=128)

        assert len(verifier) == 128

    def test_generate_code_verifier_invalid_length(self):
        """Test code verifier generation with invalid length."""
        with pytest.raises(ValueError, match="Code verifier length must be between 43 and 128"):
            generate_code_verifier(length=42)

        with pytest.raises(ValueError, match="Code verifier length must be between 43 and 128"):
            generate_code_verifier(length=129)

    def test_generate_code_challenge_s256(self, code_verifier: str):
        """Test S256 code challenge generation."""
        challenge = generate_code_challenge(code_verifier, method="S256")

        assert isinstance(challenge, str)
        assert len(challenge) == 43  # Base64url encoded SHA256 is 43 chars
        # Should be URL-safe base64
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in challenge)

    def test_generate_code_challenge_plain(self, code_verifier: str):
        """Test plain code challenge generation."""
        challenge = generate_code_challenge(code_verifier, method="plain")

        assert challenge == code_verifier

    def test_verify_code_challenge_s256(self, code_verifier: str, code_challenge: str):
        """Test S256 code challenge verification."""
        result = verify_code_challenge(code_verifier, code_challenge, method="S256")

        assert result is True

    def test_verify_code_challenge_s256_invalid(self, code_verifier: str):
        """Test S256 code challenge verification with wrong verifier."""
        wrong_challenge = "wrong_challenge_value_here_for_testing"
        result = verify_code_challenge(code_verifier, wrong_challenge, method="S256")

        assert result is False

    def test_verify_code_challenge_plain(self):
        """Test plain code challenge verification."""
        verifier = "test-verifier-123"
        challenge = "test-verifier-123"

        result = verify_code_challenge(verifier, challenge, method="plain")

        assert result is True

    def test_verify_code_challenge_plain_invalid(self):
        """Test plain code challenge verification with mismatch."""
        verifier = "test-verifier-123"
        challenge = "different-verifier"

        result = verify_code_challenge(verifier, challenge, method="plain")

        assert result is False
