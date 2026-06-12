import logging

import uvicorn

from app.common.logging_config import setup_logging
from app.config import OPS_API_ROOT, get_settings

logger = logging.getLogger("ops.runner")


def _dev_reload() -> bool:
    return get_settings().app_env.lower() in {"dev", "development", "local"}


if __name__ == "__main__":
    settings = get_settings()
    setup_logging("ops-api")
    logger.info("Starting Ops API http://%s:%s", settings.app_host, settings.app_port)

    reload = _dev_reload()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=reload,
        reload_dirs=[str(OPS_API_ROOT / "app")] if reload else None,
        reload_excludes=["logs/*", "*.log"] if reload else None,
        log_level=settings.log_level.lower(),
    )