from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql://praan_user:praan_pass@localhost:5432/praan_health"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-random-32-char-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # App
    ENVIRONMENT: str = "development"

    @property
    def upload_dir_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
