from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.common.logging_config import request_id_ctx
from app.config import get_settings

logger = logging.getLogger("ops.access")

_SKIP_PATHS = frozenset({"/health"})


def add_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next) -> Response:
        if not get_settings().log_access or request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        client_ip = request.client.host if request.client else "-"
        started = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> %s (%.2fms) client=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                client_ip,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "%s %s failed (%.2fms) client=%s",
                request.method,
                request.url.path,
                duration_ms,
                client_ip,
            )
            raise
        finally:
            request_id_ctx.reset(token)
