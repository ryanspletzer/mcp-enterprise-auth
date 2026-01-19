"""PKCE (Proof Key for Code Exchange) validation utilities."""

import base64
import hashlib

import structlog

logger = structlog.get_logger(__name__)


def validate_code_challenge_method(method: str) -> bool:
    """
    Validate PKCE code challenge method.

    Args:
        method: Code challenge method ("plain" or "S256")

    Returns:
        True if valid, False otherwise
    """
    return method in ("plain", "S256")


def verify_code_challenge(
    code_verifier: str,
    code_challenge: str,
    method: str = "S256",
) -> bool:
    """
    Verify PKCE code challenge against code verifier.

    Args:
        code_verifier: The original code verifier from client
        code_challenge: The code challenge from authorization request
        method: Challenge method ("plain" or "S256")

    Returns:
        True if verification succeeds, False otherwise
    """
    if method == "plain":
        # Plain text comparison
        result = code_verifier == code_challenge
        logger.debug(
            "pkce_verification_plain",
            result=result,
        )
        return result

    elif method == "S256":
        # SHA256 hash comparison
        # Compute: BASE64URL(SHA256(code_verifier))
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

        result = computed_challenge == code_challenge
        logger.debug(
            "pkce_verification_s256",
            result=result,
            computed_challenge=computed_challenge[:8] + "...",
            expected_challenge=code_challenge[:8] + "...",
        )
        return result

    else:
        logger.warning("pkce_verification_invalid_method", method=method)
        return False


def generate_code_verifier(length: int = 43) -> str:
    """
    Generate a PKCE code verifier.

    Args:
        length: Length of the code verifier (43-128 characters)

    Returns:
        URL-safe base64 encoded random string
    """
    if not 43 <= length <= 128:
        raise ValueError("Code verifier length must be between 43 and 128")

    # Generate random bytes
    import secrets

    num_bytes = (length * 3) // 4
    random_bytes = secrets.token_bytes(num_bytes)

    # Base64url encode and trim to desired length
    code_verifier = base64.urlsafe_b64encode(random_bytes).decode("ascii").rstrip("=")
    return code_verifier[:length]


def generate_code_challenge(code_verifier: str, method: str = "S256") -> str:
    """
    Generate a PKCE code challenge from code verifier.

    Args:
        code_verifier: The code verifier
        method: Challenge method ("plain" or "S256")

    Returns:
        Code challenge
    """
    if method == "plain":
        return code_verifier

    elif method == "S256":
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    else:
        raise ValueError(f"Invalid code challenge method: {method}")
