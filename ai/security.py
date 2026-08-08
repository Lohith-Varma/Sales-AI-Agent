"""Shared HS256 access-token validation for AI HTTP and WebSocket transports."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
from typing import Any


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_access_token(token: str | None, secret: str | None) -> dict[str, Any]:
    if not token or not secret:
        raise ValueError("access token is required")
    header_part, payload_part, signature_part = token.split(".")
    signed = f"{header_part}.{payload_part}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _decode(signature_part)):
        raise ValueError("invalid signature")
    header = json.loads(_decode(header_part))
    payload = json.loads(_decode(payload_part))
    if header.get("alg") != "HS256" or payload.get("iss") != "sales-ai-core":
        raise ValueError("invalid claims")
    if int(payload.get("exp", 0)) <= int(dt.datetime.now(dt.UTC).timestamp()):
        raise ValueError("expired token")
    return payload


__all__ = ["verify_access_token"]
