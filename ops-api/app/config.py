from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

OPS_API_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = OPS_API_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "opsai"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    @property
    def redis_password_or_none(self) -> str | None:
        value = self.redis_password.strip()
        return value or None

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    llm_api_base: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout: int = 60

    app_host: str = "127.0.0.1"
    app_port: int = 8280
    app_version: str = "0.3.0-phase3-rca"

    alert_fingerprint_ttl_seconds: int = 1800

    # 可观测后端（阶段三 Agent 工具层）
    prometheus_base_url: str = "http://127.0.0.1:9090"
    loki_base_url: str = "http://127.0.0.1:3100"
    tempo_base_url: str = "http://127.0.0.1:3200"
    jaeger_base_url: str = "http://127.0.0.1:16686"
    trace_backend: str = "tempo"
    observability_http_timeout: float = 15.0
    ecom_log_dir: str = (
        r"D:\YIBANWENJIANJI\BIANCHENG\Project\EcomAIIntelligencePlatform\ecom-api\logs"
    )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
