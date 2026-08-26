from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SYNCHRO"
    environment: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    enable_docs: bool = True
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    max_body_bytes: int = 1_048_576

    database_url: str = "sqlite:///./synchro_dev.db"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "local-dev-only-secret-key-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 14

    encryption_key: str = ""

    rate_limit_register_per_hour: int = 20
    rate_limit_login_per_window: int = 50
    rate_limit_window_seconds: int = 900
    login_max_failures: int = 3
    login_base_lock_seconds: int = 30
    login_max_lock_seconds: int = 900

    deriv_ws_url: str = "wss://api.derivws.com/trading/v1/options/ws/public"
    deriv_app_id: str = ""

    publisher_backend: str = "memory"
    tick_buffer_size: int = 10000
    tick_stream_key: str = "synchro:ticks"

    telegram_bot_token: str = ""
    stripe_secret_key: str = ""

    @model_validator(mode="after")
    def _production_guard(self):
        if self.environment == "production":
            errors = []
            if self.jwt_secret_key.startswith("local-dev-only"):
                errors.append("JWT_SECRET_KEY must be replaced in production")
            if self.debug:
                errors.append("DEBUG must be false in production")
            if len(self.encryption_key) < 32:
                errors.append("ENCRYPTION_KEY (>=32 chars) is required in production")
            if errors:
                raise ValueError(f"insecure production configuration: { '; '.join(errors) }")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
