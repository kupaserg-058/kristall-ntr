from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, читаются из переменных окружения / .env."""

    GEMINI_API_KEY: str = ""  # один ключ или несколько через запятую

    @property
    def gemini_api_keys(self) -> list[str]:
        """Список ключей Gemini (поддерживает несколько через запятую)."""
        return [k.strip() for k in self.GEMINI_API_KEY.split(",") if k.strip()]
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kristall"
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS как список (в env хранится через запятую)."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
