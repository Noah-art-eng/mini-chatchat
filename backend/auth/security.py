import time

from fastapi import HTTPException, Request

from .config import (
    get_auth_cookie_secure,
    get_auth_rate_limit_max_failures,
    get_auth_rate_limit_window_seconds,
    get_auth_secret_key,
    get_cors_origins,
    get_oauth_provider_config,
    is_production_environment,
)


_RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}


def get_client_ip(request: Request):
    """负责 get_client_ip 的函数职责。"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.client.host if request.client else "unknown"


def verify_allowed_origin(request: Request):
    """负责 verify_allowed_origin 的函数职责。"""
    origin = request.headers.get("origin")
    if not origin:
        return

    if origin not in set(get_cors_origins()):
        raise HTTPException(status_code=403, detail="origin not allowed")


def _bucket_key(kind: str, request: Request, identifier: str | None = None):
    """负责 _bucket_key 的函数职责。"""
    normalized_identifier = (identifier or "").strip().lower()
    return f"{kind}:{get_client_ip(request)}:{normalized_identifier}"


def check_auth_rate_limit(
    kind: str,
    request: Request,
    identifier: str | None = None,
):
    """负责 check_auth_rate_limit 的函数职责。"""
    key = _bucket_key(kind, request, identifier)
    now = time.monotonic()
    window = get_auth_rate_limit_window_seconds()
    attempts = [
        timestamp
        for timestamp in _RATE_LIMIT_BUCKETS.get(key, [])
        if now - timestamp < window
    ]
    _RATE_LIMIT_BUCKETS[key] = attempts

    if len(attempts) >= get_auth_rate_limit_max_failures():
        raise HTTPException(
            status_code=429,
            detail="too many authentication attempts",
        )


def record_auth_failure(
    kind: str,
    request: Request,
    identifier: str | None = None,
):
    """负责 record_auth_failure 的函数职责。"""
    key = _bucket_key(kind, request, identifier)
    now = time.monotonic()
    window = get_auth_rate_limit_window_seconds()
    _RATE_LIMIT_BUCKETS[key] = [
        timestamp
        for timestamp in _RATE_LIMIT_BUCKETS.get(key, [])
        if now - timestamp < window
    ] + [now]


def clear_auth_failures(
    kind: str,
    request: Request,
    identifier: str | None = None,
):
    """负责 clear_auth_failures 的函数职责。"""
    _RATE_LIMIT_BUCKETS.pop(_bucket_key(kind, request, identifier), None)


def reset_auth_rate_limits():
    """负责 reset_auth_rate_limits 的函数职责。"""
    _RATE_LIMIT_BUCKETS.clear()


def validate_production_auth_config():
    """负责 validate_production_auth_config 的函数职责。"""
    if not is_production_environment():
        return

    if get_auth_secret_key() == "mini-chatchat-dev-auth-secret-change-me":
        raise RuntimeError("AUTH_SECRET_KEY must be configured in production")

    if not get_auth_cookie_secure():
        raise RuntimeError("AUTH_COOKIE_SECURE=true is required in production")

    allowed_origins = get_cors_origins()
    if not allowed_origins or "*" in allowed_origins:
        raise RuntimeError("CORS_ORIGINS must be explicit in production")

    missing = []
    for provider in ("google", "github"):
        config = get_oauth_provider_config(provider)
        for key in ("client_id", "client_secret", "redirect_uri"):
            if not config.get(key):
                missing.append(f"{provider}.{key}")

    if missing:
        raise RuntimeError(
            "OAuth configuration is incomplete in production: "
            + ", ".join(missing)
        )
