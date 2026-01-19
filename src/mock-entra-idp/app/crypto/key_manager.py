"""RSA key management for JWT signing and JWKS."""

import base64
import hashlib
from datetime import datetime
from typing import Any

import structlog
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = structlog.get_logger(__name__)


class KeyManager:
    """Manages RSA key pairs for JWT signing and JWKS distribution."""

    def __init__(self) -> None:
        """Initialize key manager with a default key pair."""
        self.keys: dict[str, dict[str, Any]] = {}
        self.current_kid: str | None = None
        self._generate_initial_key()

    def _generate_initial_key(self) -> None:
        """Generate initial RSA key pair for signing."""
        kid = self._generate_kid()
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        self.keys[kid] = {
            "private_key": private_key,
            "public_key": private_key.public_key(),
            "created_at": datetime.utcnow(),
        }
        self.current_kid = kid

        logger.info(
            "rsa_key_generated",
            kid=kid,
            key_size=2048,
            algorithm="RS256",
        )

    def get_current_signing_key(self) -> tuple[bytes, str]:
        """
        Get current private key for signing JWTs.

        Returns:
            Tuple of (private_key_pem, kid)
        """
        if not self.current_kid or self.current_kid not in self.keys:
            raise ValueError("No signing key available")

        key_data = self.keys[self.current_kid]
        private_pem = key_data["private_key"].private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return private_pem, self.current_kid

    def get_jwks(self) -> dict[str, Any]:
        """
        Get JWKS (JSON Web Key Set) for public key distribution.

        Returns:
            JWKS dict compatible with Entra ID format
        """
        keys = []

        for kid, key_data in self.keys.items():
            public_key = key_data["public_key"]

            # Extract public key numbers
            public_numbers = public_key.public_numbers()

            # Convert to base64url encoding (without padding)
            n = self._int_to_base64url(public_numbers.n)
            e = self._int_to_base64url(public_numbers.e)

            # Build JWK entry
            jwk = {
                "kty": "RSA",
                "use": "sig",
                "kid": kid,
                "n": n,
                "e": e,
                "alg": "RS256",
            }

            keys.append(jwk)

        jwks = {"keys": keys}

        logger.debug(
            "jwks_generated",
            key_count=len(keys),
            current_kid=self.current_kid,
        )

        return jwks

    def rotate_key(self) -> str:
        """
        Generate and activate a new signing key.

        Returns:
            New key ID (kid)
        """
        kid = self._generate_kid()
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        self.keys[kid] = {
            "private_key": private_key,
            "public_key": private_key.public_key(),
            "created_at": datetime.utcnow(),
        }

        # Update current key
        old_kid = self.current_kid
        self.current_kid = kid

        logger.info(
            "key_rotated",
            new_kid=kid,
            old_kid=old_kid,
            total_keys=len(self.keys),
        )

        return kid

    def _generate_kid(self) -> str:
        """
        Generate a unique key ID.

        Returns:
            Key ID (16-character hex string)
        """
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]

    def _int_to_base64url(self, value: int) -> str:
        """
        Convert integer to base64url encoded string (no padding).

        Args:
            value: Integer value to encode

        Returns:
            Base64url encoded string without padding
        """
        # Convert int to bytes (big-endian)
        value_bytes = value.to_bytes(
            (value.bit_length() + 7) // 8,
            byteorder="big",
        )

        # Base64url encode and remove padding
        return base64.urlsafe_b64encode(value_bytes).decode("ascii").rstrip("=")


# Global key manager instance
_key_manager: KeyManager | None = None


def get_key_manager() -> KeyManager:
    """Get global key manager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager
