from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "designvcs-service"
    service_port: int = 8420
    service_env: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://designvcs:designvcs@postgres:5432/designvcs"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "design-assets"
    minio_secure: bool = False

    project_service_url: str = "http://project-service:8421"
    version_service_url: str = "http://version-service:8422"
    collab_service_url: str = "http://collaboration-service:8423"
    viewer_service_url: str = "http://viewer-service:8424"
    export_service_url: str = "http://export-service:8425"
    notification_service_url: str = "http://notification-service:8426"

    jwt_secret: str = "designvcs-dev-secret"
    token_exp_minutes: int = 360

    max_file_size_bytes: int = 2_147_483_648
    upload_slo_seconds: float = 5.0
    preview_slo_seconds: float = 10.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()