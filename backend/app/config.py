"""Local settings; real credentials are read only from the runtime environment."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    agent_timeout_seconds: float = Field(default=30, gt=0)
    attractions_path: Path = Path("data/attractions.json")
    trips_path: Path = Path("data/trips.json")

    @staticmethod
    def resolve_data_path(path: Path) -> Path:
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
