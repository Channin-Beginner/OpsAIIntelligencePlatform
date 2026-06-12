from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.alerts.router import router as alerts_router
from app.auth.router import router as auth_router
from app.common.exception_handlers import register_exception_handlers
from app.common.logging_config import setup_logging
from app.common.redis_client import check_redis
from app.common.request_logging import add_request_logging
from app.common.response import success
from app.config import get_settings
from app.dashboard.router import router as dashboard_router
from app.database import get_engine
from app.incidents.router import router as incidents_router
from app.incidents.router import timeline_router
from app.kb.router import router as kb_router
from app.runbook.router import execution_router as runbook_execution_router
from app.runbook.router import router as runbooks_router
from app.users.router import router as users_router
from app.webhooks.alertmanager import router as alertmanager_webhook_router
from app.webhooks.grafana import router as grafana_webhook_router

logger = setup_logging("ops-api")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Ops API starting env=%s port=%s version=%s",
        settings.app_env,
        settings.app_port,
        settings.app_version,
    )
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("MySQL connection verified")
    except Exception:
        logger.exception("MySQL connection check failed on startup")

    if check_redis():
        logger.info("Redis connection verified")
    else:
        logger.warning("Redis unavailable on startup (health will report degraded)")

    yield
    logger.info("Ops API shutting down")


app = FastAPI(
    title="OpsAI Intelligence Platform API",
    version=settings.app_version,
    description="运维智脑平台 ops-api",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8290",
        "http://127.0.0.1:8295",
        "http://localhost:8290",
        "http://localhost:8295",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_request_logging(app)
register_exception_handlers(app)


@app.get("/health", tags=["Health"])
def get_health():
    redis_ok = check_redis()
    return success(
        data={
            "status": "ok" if redis_ok else "degraded",
            "service": "ops-api",
            "version": settings.app_version,
        }
    )


app.include_router(alertmanager_webhook_router)
app.include_router(grafana_webhook_router)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(timeline_router)
app.include_router(runbooks_router)
app.include_router(runbook_execution_router)
app.include_router(kb_router)
app.include_router(dashboard_router)
app.include_router(users_router)
