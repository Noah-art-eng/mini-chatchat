import os


def get_auth_secret_key():
    return (
        os.getenv("AUTH_SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or "mini-chatchat-dev-auth-secret-change-me"
    )


def get_auth_issuer():
    return os.getenv("AUTH_ISSUER", "mini-chatchat")


def get_access_token_expire_minutes():
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
    return os.getenv("AUTH_COOKIE_NAME", "mini_chatchat_refresh")


def get_auth_cookie_secure():
    return os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def get_auth_cookie_samesite():
    value = os.getenv("AUTH_COOKIE_SAMESITE", "lax").strip().lower()
    return value if value in {"lax", "strict", "none"} else "lax"


def get_auth_cookie_domain():
    return os.getenv("AUTH_COOKIE_DOMAIN") or None


def get_auth_cookie_path():
    return os.getenv("AUTH_COOKIE_PATH", "/auth")


def get_cors_origins():
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
    return (
        os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("MINI_CHATCHAT_ENV")
        or "development"
    ).strip().lower()


def is_production_environment():
    return get_app_environment() in {"prod", "production"}


def is_auth_configured_for_production():
    return get_auth_secret_key() != "mini-chatchat-dev-auth-secret-change-me"


def get_auth_rate_limit_max_failures():
    raw_value = os.getenv("AUTH_RATE_LIMIT_MAX_FAILURES", "5")

    try:
        return max(1, int(raw_value))
    except ValueError:
        return 5


def get_auth_rate_limit_window_seconds():
    raw_value = os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300")

    try:
        return max(30, int(raw_value))
    except ValueError:
        return 300


def get_frontend_base_url():
    return os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173").rstrip("/")


def get_backend_base_url():
    return os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def get_oauth_provider_config(provider: str):
    provider_key = provider.upper()
    return {
        "client_id": os.getenv(f"{provider_key}_CLIENT_ID", ""),
        "client_secret": os.getenv(f"{provider_key}_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv(
            f"{provider_key}_REDIRECT_URI",
            f"{get_backend_base_url()}/auth/oauth/{provider}/callback",
        ),
    }
