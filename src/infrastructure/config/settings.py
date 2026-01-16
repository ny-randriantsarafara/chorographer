"""Application settings using pydantic-settings."""

from pathlib import Path
from functools import lru_cache
import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find project root directory (where .env is located)
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_project_root / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OSM
    osm_file_path: Path = Path("data/madagascar-latest.osm.pbf")

    # PostgreSQL (lemurion database)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "lemurion"
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("")

    # Processing
    batch_size: int = 1000

    # Parallel processing
    enable_parallel_pipeline: bool = True
    parallel_queue_depth: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: str = "console"  # "json" or "console"

    @property
    def postgres_dsn(self) -> str:
        """Build PostgreSQL connection string."""
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_postgres_dsn(self) -> str:
        """Build async PostgreSQL connection string."""
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience alias
settings = get_settings()
