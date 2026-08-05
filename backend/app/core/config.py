from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CargoPilot"
    app_env: str = "production"
    app_secret_key: str = "change-me"
    database_url: str = "sqlite:////data/cargopilot.db"
    data_dir: Path = Path("/data")
    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    log_level: str = "INFO"
    cors_allowed_origins: str = "*"
    trusted_proxy_headers: bool = True
    access_token_expire_minutes: int = 480
    cookie_secure: bool | None = None
    max_paste_bytes: int = 512_000
    catalog_auto_sync: bool = True
    catalog_sync_timeout_seconds: float = 20.0
    geo_address_api_url: str = "https://photon.komoot.io/api"
    geo_address_timeout_seconds: float = 8.0

    @property
    def templates_dir(self) -> Path:
        return self.data_dir / "templates"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def seed_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "seed"

    @property
    def config_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "config"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "static"

    @property
    def repo_templates_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".." / "templates"

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def secure_cookies(self) -> bool:
        """Use Secure cookies by default outside local development and tests.

        ``COOKIE_SECURE`` remains an explicit escape hatch for unusual reverse
        proxy setups, but a production installation no longer silently emits a
        session cookie that browsers may send over plain HTTP.
        """
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.app_env.strip().lower() not in {"test", "development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
