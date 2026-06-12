from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "X- Audio Guest Booth"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://booth:booth@localhost:5432/aiguestbooth"

    storage_backend: str = "local"
    storage_path: str = "../storage"

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    cors_origins: str = "http://localhost:3000"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_whisper_model: str = "whisper-1"
    ai_pipeline_enabled: bool = True

    s3_bucket: str = ""
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_snapshot_bytes: int = 5 * 1024 * 1024  # 5 MB
    public_api_url: str = "http://localhost:8000"
    frontend_public_url: str = "http://localhost:3000"
    firmware_latest_version: str = "0.2.0"
    firmware_download_url: str = ""
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "nova"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
