import base64
import hashlib
import hmac
import json
import uuid
import time
from typing import Any

from .config import (
    get_access_token_expire_minutes,
    get_auth_issuer,
    get_auth_secret_key,
    get_refresh_token_expire_days,
)


class JWTError(Exception):
    """负责 JWTError 的类职责。"""
    pass


def _base64url_encode(raw_bytes: bytes):
    """负责 _base64url_encode 的函数职责。"""
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str):
    """负责 _base64url_decode 的函数职责。"""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _json_encode(payload: dict[str, Any]):
    """负责 _json_encode 的函数职责。"""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def create_access_token(
    subject: str,
    claims: dict[str, Any] | None = None,
    expires_in_minutes: int | None = None,
):
    """负责 create_access_token 的函数职责。"""
    now = int(time.time())
    expire_minutes = expires_in_minutes or get_access_token_expire_minutes()
    payload = {
        "iss": get_auth_issuer(),
        "sub": subject,
        "iat": now,
        "exp": now + expire_minutes * 60,
        "token_type": "access",
        **(claims or {}),
    }
    return _encode_jwt(payload)


def create_refresh_token(
    subject: str,
    session_id: str,
    claims: dict[str, Any] | None = None,
    expires_in_days: int | None = None,
):
    """负责 create_refresh_token 的函数职责。"""
    now = int(time.time())
    expire_days = expires_in_days or get_refresh_token_expire_days()
    payload = {
        "iss": get_auth_issuer(),
        "sub": subject,
        "iat": now,
        "exp": now + expire_days * 24 * 60 * 60,
        "token_type": "refresh",
        "session_id": session_id,
        "jti": str(uuid.uuid4()),
        **(claims or {}),
    }
    return _encode_jwt(payload)


def _encode_jwt(payload: dict[str, Any]):
    """负责 _encode_jwt 的函数职责。"""
    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    signing_input = ".".join([
        _base64url_encode(_json_encode(header)),
        _base64url_encode(_json_encode(payload)),
    ])
    signature = hmac.new(
        get_auth_secret_key().encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return f"{signing_input}.{_base64url_encode(signature)}"


def decode_token(token: str):
    """负责 decode_token 的函数职责。"""
    try:
        header_text, payload_text, signature_text = token.split(".", 2)
    except ValueError as exc:
        raise JWTError("invalid token format") from exc

    signing_input = f"{header_text}.{payload_text}"
    expected_signature = hmac.new(
        get_auth_secret_key().encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        actual_signature = _base64url_decode(signature_text)
    except (ValueError, TypeError) as exc:
        raise JWTError("invalid token signature") from exc

    if not hmac.compare_digest(actual_signature, expected_signature):
        raise JWTError("invalid token signature")

    try:
        header = json.loads(_base64url_decode(header_text))
        payload = json.loads(_base64url_decode(payload_text))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise JWTError("invalid token payload") from exc

    if header.get("alg") != "HS256":
        raise JWTError("unsupported token algorithm")

    if payload.get("iss") != get_auth_issuer():
        raise JWTError("invalid token issuer")

    if int(payload.get("exp", 0)) < int(time.time()):
        raise JWTError("token expired")

    return payload


def decode_access_token(token: str):
    """负责 decode_access_token 的函数职责。"""
    payload = decode_token(token)

    if payload.get("token_type") != "access":
        raise JWTError("invalid token type")

    return payload


def decode_refresh_token(token: str):
    """负责 decode_refresh_token 的函数职责。"""
    payload = decode_token(token)

    if payload.get("token_type") != "refresh":
        raise JWTError("invalid token type")

    return payload
