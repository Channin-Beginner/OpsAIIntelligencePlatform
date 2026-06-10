from typing import Any, Generic, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class CommonResult(BaseModel, Generic[T]):
    code: int
    message: str
    data: T | None = None


def success(data: Any = None, message: str = "操作成功", code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data}


def error(
    message: str,
    code: int,
    data: Any = None,
) -> dict:
    return {"code": code, "message": message, "data": data}


def http_error_response(
    request: Request,
    status_code: int,
    message: str,
    code: int,
    data: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error(message=message, code=code, data=data),
    )
