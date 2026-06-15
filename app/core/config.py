from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "My API"
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/db"
    secret_key: str = "change-me-in-production"
    debug: bool = False
    seed_db: bool = False

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    s3_private_bucket: str = ""
    s3_public_bucket: str = ""
    s3_presigned_expiry: int = 3600

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    anthropic_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
