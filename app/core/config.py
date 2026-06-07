from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "My API"
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/db"
    secret_key: str = "change-me-in-production"
    debug: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
