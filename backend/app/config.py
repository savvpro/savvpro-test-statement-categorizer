from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Statement Categorizer"
    debug: bool = True


settings = Settings()