import os
import warnings
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _clean(value: str | None, default: str = "") -> str:
    return (value if value is not None else default).strip()


@lru_cache(maxsize=1)
def get_settings() -> dict[str, object]:
    environment = _clean(os.getenv("ENVIRONMENT"), "development").lower()
    port = int(_clean(os.getenv("PORT"), "8000"))
    database_url = _clean(os.getenv("DATABASE_URL"))

    if not database_url:
        if environment == "production":
            raise ValueError(
                "FATAL: DATABASE_URL environment variable must be set in production."
            )
        warnings.warn(
            "Using local SQLite database. Set DATABASE_URL to test with PostgreSQL/Supabase.",
            RuntimeWarning,
        )
        database_url = "sqlite+aiosqlite:///./nandu.db"

    if environment == "production" and "sqlite" in database_url.lower():
        raise ValueError(
            "FATAL: SQLite is not supported in production. Set DATABASE_URL to PostgreSQL/MySQL."
        )

    secret_key = _clean(os.getenv("SECRET_KEY"))
    if not secret_key:
        if environment == "production":
            raise ValueError(
                "FATAL: SECRET_KEY environment variable must be set in production."
            )
        warnings.warn(
            "Using development fallback SECRET_KEY. Set SECRET_KEY for production.",
            RuntimeWarning,
        )
        secret_key = "dev-only-fallback-key-change-for-production"

    admin_email = _clean(os.getenv("ADMIN_EMAIL"), "admin@nandutravels.com")
    admin_password = _clean(os.getenv("ADMIN_PASSWORD"), "Admin@Nandu2026")
    if environment == "production" and admin_password == "Admin@Nandu2026":
        raise ValueError(
            "FATAL: ADMIN_PASSWORD must be overridden in production."
        )

    app_base_url = _clean(os.getenv("APP_BASE_URL"))
    vercel_url = _clean(os.getenv("VERCEL_URL"))
    if not app_base_url and vercel_url:
        app_base_url = f"https://{vercel_url}"
    if not app_base_url:
        app_base_url = f"http://localhost:{port}"

    raw_cors = _clean(os.getenv("CORS_ORIGINS"))
    if raw_cors:
        cors_origins = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]
    elif environment == "production":
        cors_origins = [app_base_url]
    else:
        cors_origins = [
            f"http://localhost:{port}",
            f"http://127.0.0.1:{port}",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
        ]

    return {
        "environment": environment,
        "port": port,
        "database_url": database_url,
        "secret_key": secret_key,
        "algorithm": _clean(os.getenv("ALGORITHM"), "HS256"),
        "access_token_expire_minutes": int(_clean(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), "10080")),
        "admin_email": admin_email,
        "admin_password": admin_password,
        "google_client_id": _clean(os.getenv("GOOGLE_CLIENT_ID")),
        "google_client_secret": _clean(os.getenv("GOOGLE_CLIENT_SECRET")),
        "google_redirect_uri": _clean(os.getenv("GOOGLE_REDIRECT_URI")),
        "supabase_url": _clean(os.getenv("SUPABASE_URL")),
        "supabase_service_role_key": _clean(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "profile_upload_bucket": _clean(os.getenv("SUPABASE_PROFILE_BUCKET"), "user-profiles"),
        "driver_docs_bucket": _clean(os.getenv("SUPABASE_DRIVER_DOCS_BUCKET"), "driver-docs"),
        "max_file_size_bytes": int(_clean(os.getenv("MAX_FILE_SIZE_BYTES"), "5242880")),
        "min_driver_app_version": _clean(os.getenv("MIN_DRIVER_APP_VERSION"), "1.0.0"),
        "cors_origins": cors_origins,
        "app_base_url": app_base_url.rstrip("/"),
    }


settings = get_settings()