from __future__ import annotations

import base64

from mcp_sentinel.auth import (
    API_KEY_PREFIX,
    PBKDF2_ITERATIONS,
    PBKDF2_SCHEME,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)


def test_generate_api_key_has_expected_prefix() -> None:
    api_key = generate_api_key()

    assert api_key.startswith(API_KEY_PREFIX)
    assert len(api_key) > len(API_KEY_PREFIX)


def test_hash_round_trip_verifies_presented_key() -> None:
    api_key = generate_api_key()
    stored_hash = hash_api_key(api_key)

    assert verify_api_key(api_key, stored_hash)


def test_wrong_key_fails_verification() -> None:
    api_key = generate_api_key()
    stored_hash = hash_api_key(api_key)

    assert not verify_api_key(f"{api_key}x", stored_hash)


def test_hash_output_format_contains_scheme_iterations_salt_and_digest() -> None:
    stored_hash = hash_api_key(generate_api_key())

    scheme, iterations_text, salt_b64, digest_b64 = stored_hash.split("$", maxsplit=3)

    assert scheme == PBKDF2_SCHEME
    assert int(iterations_text) == PBKDF2_ITERATIONS
    assert base64.b64decode(salt_b64.encode("ascii"), validate=True)
    assert base64.b64decode(digest_b64.encode("ascii"), validate=True)
