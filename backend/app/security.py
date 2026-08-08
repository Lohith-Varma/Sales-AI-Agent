"""Minimal dependency-free password hashing and HS256 JWT authentication."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import HTTPException, Request

from app.config import settings
from app.db.base import User
from app.db.database import SessionLocal


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("password must contain at least 12 characters")
    salt = os.urandom(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.urlsafe_b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (TypeError, ValueError):
        return False


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_access_token(user: User) -> str:
    if not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not configured")
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=settings.JWT_ACCESS_MINUTES)).timestamp()),
        "iss": "sales-ai-core",
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded = f"{_b64encode(json.dumps(header, separators=(',', ':')).encode())}.{_b64encode(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(settings.JWT_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    if not settings.JWT_SECRET:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    try:
        header_part, payload_part, signature_part = token.split(".")
        encoded = f"{header_part}.{payload_part}"
        expected = hmac.new(settings.JWT_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(signature_part)):
            raise ValueError("signature")
        header = json.loads(_b64decode(header_part))
        payload = json.loads(_b64decode(payload_part))
        if header.get("alg") != "HS256" or payload.get("iss") != "sales-ai-core":
            raise ValueError("claims")
        if int(payload.get("exp", 0)) <= int(dt.datetime.now(dt.UTC).timestamp()):
            raise ValueError("expired")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def authenticate_request(request: Request) -> User | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        if settings.AUTH_REQUIRED:
            raise HTTPException(status_code=401, detail="Bearer access token required")
        return None
    claims = decode_access_token(authorization.split(" ", 1)[1].strip())
    try:
        user_id = claims["sub"]
        with SessionLocal() as db:
            user = db.get(User, user_id)
            if user is None or not user.is_active:
                raise HTTPException(status_code=401, detail="User is inactive or missing")
            db.expunge(user)
            return user
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token claims") from exc


__all__ = [
    "authenticate_request",
    "decode_access_token",
    "hash_password",
    "issue_access_token",
    "verify_password",
]
