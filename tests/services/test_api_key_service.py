"""
Tests for apps/api/app/services/api_key_service.py
"""

import hashlib

from apps.api.app.services.api_key_service import (
    KEY_PREFIX,
    generate_api_key,
)


class TestGenerateApiKey:
    def test_format(self):
        """Key starts with xv_live_ and has 32 hex chars after prefix."""
        raw_key, _, _ = generate_api_key()
        assert raw_key.startswith(KEY_PREFIX)
        hex_part = raw_key[len(KEY_PREFIX):]
        assert len(hex_part) == 32
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_hash_consistency(self):
        """SHA256(raw_key) == key_hash."""
        raw_key, key_hash, _ = generate_api_key()
        assert hashlib.sha256(raw_key.encode()).hexdigest() == key_hash

    def test_prefix_matches(self):
        """key_prefix is first 8 hex chars after 'xv_live_'."""
        raw_key, _, key_prefix = generate_api_key()
        hex_part = raw_key[len(KEY_PREFIX):]
        assert key_prefix == f"{KEY_PREFIX}{hex_part[:8]}"

    def test_uniqueness(self):
        """1000 generated keys are all unique."""
        keys = {generate_api_key()[0] for _ in range(1000)}
        assert len(keys) == 1000

    def test_hash_not_equal_to_key(self):
        """The hash must differ from the raw key."""
        raw_key, key_hash, _ = generate_api_key()
        assert raw_key != key_hash
