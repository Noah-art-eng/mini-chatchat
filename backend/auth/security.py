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
    """从可信请求信息中取得客户端地址，供登录限流和会话记录使用。"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.client.host if request.client else "unknown"


def verify_allowed_origin(request: Request):
    """校验敏感认证请求的 Origin，降低跨站请求伪造风险。"""
    origin = request.headers.get("origin")
    if not origin:
        return

    if origin not in set(get_cors_origins()):
        raise HTTPException(status_code=403, detail="origin not allowed")


def _bucket_key(kind: str, request: Request, identifier: str | None = None):
    """把邮箱与客户端地址组合成登录限流键，避免一个维度影响所有用户。"""
    normalized_identifier = (identifier or "").strip().lower()
    return f"{kind}:{get_client_ip(request)}:{normalized_identifier}"


def check_auth_rate_limit(
    kind: str,
    request: Request,
    identifier: str | None = None,
):
    """检查当前登录失败次数；窗口内超过上限时直接拒绝继续尝试。"""
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
    """记录一次认证失败，并从首次失败时间开始计算限流窗口。"""
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
    """登录成功后清除对应限流记录。"""
    _RATE_LIMIT_BUCKETS.pop(_bucket_key(kind, request, identifier), None)


def reset_auth_rate_limits():
    """清空进程内限流状态，供隔离测试重新建立基线。"""
    _RATE_LIMIT_BUCKETS.clear()


def validate_production_auth_config():
    """生产环境启动时检查密钥、Cookie 和 CORS 配置，错误配置直接失败。"""
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
