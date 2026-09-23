import os


def get_auth_secret_key():
    """负责 get_auth_secret_key 的函数职责。"""
    return (
        os.getenv("AUTH_SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or "mini-chatchat-dev-auth-secret-change-me"
    )


def get_auth_issuer():
    """负责 get_auth_issuer 的函数职责。"""
    return os.getenv("AUTH_ISSUER", "mini-chatchat")


def get_access_token_expire_minutes():
    """负责 get_access_token_expire_minutes 的函数职责。"""
    raw_value = (
        os.getenv("ACCESS_TOKEN_TTL_MINUTES")
        or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
        or "15"
    )

    try:
        return max(1, int(raw_value))
    except ValueError:
        return 15


def get_refresh_token_expire_days():
    """负责 get_refresh_token_expire_days 的函数职责。"""
    raw_value = (
        os.getenv("REFRESH_TOKEN_TTL_DAYS")
        or os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")
        or "30"
    )

    try:
        return max(1, int(raw_value))
    except ValueError:
        return 30


def get_auth_cookie_name():
    """负责 get_auth_cookie_name 的函数职责。"""
    return os.getenv("AUTH_COOKIE_NAME", "mini_chatchat_refresh")


def get_auth_cookie_secure():
    """负责 get_auth_cookie_secure 的函数职责。"""
    return os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def get_auth_cookie_samesite():
    """负责 get_auth_cookie_samesite 的函数职责。"""
    value = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    return value if value in {"lax", "strict", "none"} else "lax"


def get_auth_cookie_domain():
    """负责 get_auth_cookie_domain 的函数职责。"""
    return os.getenv("AUTH_COOKIE_DOMAIN") or None


def get_auth_cookie_path():
    """负责 get_auth_cookie_path 的函数职责。"""
    return os.getenv("AUTH_COOKIE_PATH", "/auth")


def get_cors_origins():
    """负责 get_cors_origins 的函数职责。"""
    raw_value = os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    return [
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    ]


def get_app_environment():
    """负责 get_app_environment 的函数职责。"""
    return (
        os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("MINI_CHATCHAT_ENV")
        or "development"
    ).strip().lower()


def is_production_environment():
    """负责 is_production_environment 的函数职责。"""
    return get_app_environment() in {"prod", "production"}


def is_auth_configured_for_production():
    """负责 is_auth_configured_for_production 的函数职责。"""
    return get_auth_secret_key() != "mini-chatchat-dev-auth-secret-change-me"


def get_auth_rate_limit_max_failures():
    """负责 get_auth_rate_limit_max_failures 的函数职责。"""
    raw_value = os.getenv("AUTH_RATE_LIMIT_MAX_FAILURES", "5")

    try:
        return max(1, int(raw_value))
    except ValueError:
        return 5


def get_auth_rate_limit_window_seconds():
    """负责 get_auth_rate_limit_window_seconds 的函数职责。"""
    raw_value = os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300")

    try:
        return max(30, int(raw_value))
    except ValueError:
        return 300


def get_frontend_base_url():
    """负责 get_frontend_base_url 的函数职责。"""
    return os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173").rstrip("/")


def get_backend_base_url():
    """负责 get_backend_base_url 的函数职责。"""
    return os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def get_oauth_provider_config(provider: str):
    """负责 get_oauth_provider_config 的函数职责。"""
    provider_key = provider.upper()
    return {
        "client_id": os.getenv(f"{provider_key}_CLIENT_ID", ""),
        "client_secret": os.getenv(f"{provider_key}_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv(
            f"{provider_key}_REDIRECT_URI",
            f"{get_backend_base_url()}/auth/oauth/{provider}/callback",
        ),
    }
