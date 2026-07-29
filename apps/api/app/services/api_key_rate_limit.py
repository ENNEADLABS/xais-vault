"""
Per-API-key rate limiting via CacheBackend.

Tracks RPM (requests per minute) and RPD (requests per day) per API key ID.
Redis (production multi-instance) ou in-memory (dev/test).
"""

import logging

from packages.db.redis_client import get_cache

logger = logging.getLogger(__name__)


async def check_api_key_rate_limit(
    api_key_id: str,
    rpm_limit: int,
    rpd_limit: int,
) -> tuple[bool, str]:
    """Vérifie les limites RPM et RPD pour une API key.

    Returns:
        (allowed, error_message) — error_message est "" si allowed.
    """
    cache = get_cache()

    rpm_key = f"rl:key:{api_key_id}:rpm"
    rpd_key = f"rl:key:{api_key_id}:rpd"

    rpm_count = await cache.incr(rpm_key)
    if rpm_count == 1:
        await cache.expire(rpm_key, 60)

    rpd_count = await cache.incr(rpd_key)
    if rpd_count == 1:
        await cache.expire(rpd_key, 86400)

    if rpm_count > rpm_limit:
        ttl = await cache.ttl(rpm_key)
        return False, f"RPM limit ({rpm_limit}/min) exceeded. Retry in {ttl}s."

    if rpd_count > rpd_limit:
        ttl = await cache.ttl(rpd_key)
        return False, f"RPD limit ({rpd_limit}/day) exceeded. Retry in {ttl}s."

    return True, ""
