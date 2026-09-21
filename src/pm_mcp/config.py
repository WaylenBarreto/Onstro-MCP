from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class AppSettings:
    pm_api_base_url: str = "http://localhost:5000/api"
    pm_api_key: str = ""
    pm_api_timeout: int = 30
    pm_api_retries: int = 3
    mock_mode: bool = True
    log_level: str = "INFO"
    groq_api_key: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    pm_api_base_url: str = Field(default="http://localhost:5000/api", alias="PM_API_BASE_URL")
    pm_api_key: SecretStr | None = Field(default=None, alias="PM_API_KEY")
    pm_api_timeout: int = Field(default=30, alias="PM_API_TIMEOUT")
    pm_api_retries: int = Field(default=3, alias="PM_API_RETRIES")
    mock_mode: bool = Field(default=True, alias="MOCK_MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")

    @field_validator("pm_api_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if not value:
            return "http://localhost:5000/api"
        return value.rstrip("/")

    @property
    def api_key_value(self) -> str:
        return self.pm_api_key.get_secret_value() if self.pm_api_key else ""

    @property
    def groq_api_key_value(self) -> str:
        return self.groq_api_key.get_secret_value() if self.groq_api_key else ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_app_settings() -> AppSettings:
    settings = get_settings()
    return AppSettings(
        pm_api_base_url=settings.pm_api_base_url,
        pm_api_key=settings.api_key_value,
        pm_api_timeout=settings.pm_api_timeout,
        pm_api_retries=settings.pm_api_retries,
        mock_mode=settings.mock_mode,
        log_level=settings.log_level,
        groq_api_key=settings.groq_api_key_value,
    )
