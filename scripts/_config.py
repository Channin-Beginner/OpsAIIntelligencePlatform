"""Shared configuration for chaos / seed scripts (阶段二 2.C)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_API_ROOT = REPO_ROOT / "ops-api"
SEED_OUTPUT_DIR = REPO_ROOT / "灌注数据"

# Load ops-api/.env first, then optional scripts/.env override.
load_dotenv(OPS_API_ROOT / ".env")
load_dotenv(REPO_ROOT / "scripts" / ".env", override=True)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class MysqlConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class ScriptConfig:
    ops_mysql: MysqlConfig
    ecom_mysql: MysqlConfig
    ecom_admin_base_url: str
    ecom_portal_base_url: str
    ecom_api_repo_path: Path | None
    seed_output_dir: Path

    @classmethod
    def load(cls) -> "ScriptConfig":
        repo_path_raw = _env("ECOM_API_REPO_PATH")
        repo_path = Path(repo_path_raw) if repo_path_raw else None

        ops_password = _env("MYSQL_PASSWORD")
        ecom_password = _env("ECOM_MYSQL_PASSWORD", ops_password)

        return cls(
            ops_mysql=MysqlConfig(
                host=_env("MYSQL_HOST", "127.0.0.1"),
                port=int(_env("MYSQL_PORT", "3306")),
                user=_env("MYSQL_USER", "root"),
                password=ops_password,
                database=_env("MYSQL_DATABASE", "opsai"),
            ),
            ecom_mysql=MysqlConfig(
                host=_env("ECOM_MYSQL_HOST", _env("MYSQL_HOST", "127.0.0.1")),
                port=int(_env("ECOM_MYSQL_PORT", _env("MYSQL_PORT", "3306"))),
                user=_env("ECOM_MYSQL_USER", _env("MYSQL_USER", "root")),
                password=ecom_password,
                database=_env("ECOM_MYSQL_DATABASE", "ecomai"),
            ),
            ecom_admin_base_url=_env("ECOM_ADMIN_BASE_URL", "http://127.0.0.1:8081"),
            ecom_portal_base_url=_env("ECOM_PORTAL_BASE_URL", "http://127.0.0.1:8085"),
            ecom_api_repo_path=repo_path,
            seed_output_dir=Path(_env("SEED_OUTPUT_DIR", str(SEED_OUTPUT_DIR))),
        )


def ensure_seed_output_dir(config: ScriptConfig) -> Path:
    config.seed_output_dir.mkdir(parents=True, exist_ok=True)
    return config.seed_output_dir
