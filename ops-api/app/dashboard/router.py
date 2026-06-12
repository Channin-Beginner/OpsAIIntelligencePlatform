from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.response import success
from app.dashboard.service import get_dashboard_overview, refresh_ads_tables
from app.database import get_db
from app.models.sys_user import SysUser

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/overview")
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    overview = get_dashboard_overview(db)
    return success(data=overview.model_dump())


@router.post("/refresh-ads")
def post_refresh_ads(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    days: int = Query(90, ge=1, le=365),
):
    if current_user.role != "admin":
        from app.common.exceptions import ForbiddenError

        raise ForbiddenError(message="需要管理员权限")
    result = refresh_ads_tables(db, days=days)
    return success(data=result)
