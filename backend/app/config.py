import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Statement Categorizer API"
    environment: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    max_file_size_mb: int = 10
    allowed_extensions: list[str] = [".csv", ".txt"]
    confidence_threshold: float = 0.75
    fuzzy_match_threshold: float = 82.0
    data_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
