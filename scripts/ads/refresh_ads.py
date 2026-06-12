"""从 incident + alert + feedback 聚合刷新 ads_* 表（阶段五 5.6）。"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPS_API_ROOT = REPO_ROOT / "ops-api"
sys.path.insert(0, str(OPS_API_ROOT))

from app.config import get_settings  # noqa: E402
from app.dashboard.service import refresh_ads_tables  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Refresh OpsAI ADS tables")
    parser.add_argument("--days", type=int, default=90, help="回溯天数")
    args = parser.parse_args()

    _ = get_settings()
    db = SessionLocal()
    try:
        result = refresh_ads_tables(db, days=args.days)
        print(f"ADS refresh completed: {result}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
