from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.alerts.service import list_alerts
from app.common.deps import get_current_user
from app.common.response import success
from app.database import get_db
from app.models.sys_user import SysUser

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("")
def get_alerts(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    service: str | None = None,
    fingerprint: str | None = None,
    keyword: str | None = None,
):
    result = list_alerts(
        db,
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        source=source,
        service=service,
        fingerprint=fingerprint,
        keyword=keyword,
    )
    return success(data=result.model_dump())
