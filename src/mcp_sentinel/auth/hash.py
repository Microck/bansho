from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

PBKDF2_SCHEME = "pbkdf2_sha256"
PBKDF2_DIGEST = "sha256"
PBKDF2_ITERATIONS = 210_000
API_KEY_PREFIX = "msl_"
_SALT_BYTES = 16
_TOKEN_BYTES = 32


def generate_api_key(prefix: str = API_KEY_PREFIX) -> str:
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    return f"{prefix}{token}"


def hash_api_key(api_key: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(PBKDF2_DIGEST, api_key.encode("utf-8"), salt, iterations)
    salt_b64 = _to_b64_ascii(salt)
    digest_b64 = _to_b64_ascii(digest)
    return f"{PBKDF2_SCHEME}${iterations}${salt_b64}${digest_b64}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    try:
        scheme, iterations_text, salt_b64, digest_b64 = stored_hash.split("$", maxsplit=3)
        if scheme != PBKDF2_SCHEME:
            return False

        iterations = int(iterations_text)
        if iterations < 1:
            return False

        salt = _from_b64_ascii(salt_b64)
        expected_digest = _from_b64_ascii(digest_b64)
    except (TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(PBKDF2_DIGEST, api_key.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual_digest, expected_digest)


def _to_b64_ascii(raw_value: bytes) -> str:
    return base64.b64encode(raw_value).decode("ascii")


def _from_b64_ascii(encoded_value: str) -> bytes:
    return base64.b64decode(encoded_value.encode("ascii"), validate=True)
