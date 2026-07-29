"""
Webhook security helpers — SSRF validation + HMAC-SHA256 signing.
Extracted from webhook_dispatcher.py.
"""

import hashlib
import hmac
import ipaddress
import socket
from urllib.parse import urlparse


def validate_webhook_url(url: str) -> None:
    """Bloque les URLs pointant vers des IPs privées, loopback ou link-local (anti-SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    # Rejeter les URLs avec credentials (SSRF defense-in-depth)
    if parsed.username or parsed.password:
        raise ValueError("Webhook URL must not contain credentials")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    try:
        resolved_ips = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    for _, _, _, _, sockaddr in resolved_ips:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"Webhook URL resolves to blocked IP: {ip}")


def sign_payload(secret: str, body: bytes) -> str:
    """Sign the body with HMAC-SHA256.

    Recipients verify with:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert expected == request.headers["X-Webhook-Signature"]
    """
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
