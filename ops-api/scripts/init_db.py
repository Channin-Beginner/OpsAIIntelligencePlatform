"""执行 sql/ddl 建库与种子用户（从 ops-api/.env 读取 MySQL 配置）。"""

import os
import sys

from pathlib import Path

OPS_API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = OPS_API_ROOT.parent
sys.path.insert(0, str(OPS_API_ROOT))

from app.config import get_settings  # noqa: E402

DDL_FILES = [
    "00_database.sql",
    "01_sys_user.sql",
    "02_alert_event.sql",
    "03_incident.sql",
    "04_incident_timeline.sql",
    "05_incident_alert_rel.sql",
    "99_seed_users.sql",
]


def main() -> None:
    import pymysql

    settings = get_settings()
    ddl_dir = REPO_ROOT / "sql" / "ddl"
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cursor:
            for name in DDL_FILES:
                path = ddl_dir / name
                sql = path.read_text(encoding="utf-8")
                print(f"Executing {name}...")
                for raw in sql.split(";"):
                    lines = [
                        line
                        for line in raw.splitlines()
                        if line.strip() and not line.strip().startswith("--")
                    ]
                    statement = "\n".join(lines).strip()
                    if statement:
                        cursor.execute(statement)
        print("Database init completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
