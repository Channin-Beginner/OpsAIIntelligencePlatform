from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.alerts.router import router as alerts_router
from app.auth.router import router as auth_router
from app.common.exceptions import AppError
from app.common.redis_client import check_redis
from app.common.response import error, success
from app.config import get_settings
from app.incidents.router import router as incidents_router
from app.incidents.router import timeline_router
from app.users.router import router as users_router
from app.webhooks.alertmanager import router as webhooks_router

settings = get_settings()

app = FastAPI(
    title="OpsAI Intelligence Platform API",
    version=settings.app_version,
    description="运维智脑平台 ops-api",
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


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error(message=exc.message, code=exc.code, data=exc.data),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error(
            message="请求参数校验失败",
            code=400,
            data={"errors": exc.errors()},
        ),
    )


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


app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(timeline_router)
app.include_router(users_router)
