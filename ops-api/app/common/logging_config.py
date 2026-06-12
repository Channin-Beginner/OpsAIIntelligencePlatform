from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import OPS_API_ROOT, get_settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
service_ctx: ContextVar[str] = ContextVar("service", default="-")

_initialized: set[str] = set()


class _ServiceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.service = service_ctx.get()
        record.request_id = request_id_ctx.get()
        return True


class _TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.service = getattr(record, "service", service_ctx.get())
        record.request_id = getattr(record, "request_id", request_id_ctx.get())
        return super().format(record)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", service_ctx.get()),
            "request_id": getattr(record, "request_id", request_id_ctx.get()),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _build_handlers(service: str, formatter: logging.Formatter) -> list[logging.Handler]:
    settings = get_settings()
    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_ServiceFilter())
    handlers.append(stream_handler)

    if settings.log_file_enabled:
        log_dir = Path(settings.log_dir)
        if not log_dir.is_absolute():
            log_dir = OPS_API_ROOT / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / f"{service}.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(_ServiceFilter())
        handlers.append(file_handler)

    return handlers


def setup_logging(service: str) -> logging.Logger:
    """Configure application logging once per process."""
    if service in _initialized:
        return logging.getLogger("ops")

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    service_ctx.set(service)

    if settings.log_format.lower() == "json":
        formatter: logging.Formatter = _JsonFormatter()
    else:
        text_format = (
            "%(asctime)s %(levelname)s [%(service)s] [%(request_id)s] %(name)s: %(message)s"
        )
        formatter = _TextFormatter(text_format, datefmt="%Y-%m-%d %H:%M:%S")

    handlers = _build_handlers(service, formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    for handler in handlers:
        root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level)

    if settings.log_access:
        logging.getLogger("uvicorn.access").disabled = True

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    _initialized.add(service)
    app_logger = logging.getLogger("ops")
    app_logger.info(
        "Logging initialized service=%s level=%s format=%s",
        service,
        settings.log_level,
        settings.log_format,
    )
    return app_logger
