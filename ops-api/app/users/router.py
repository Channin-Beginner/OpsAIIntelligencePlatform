from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.exceptions import ForbiddenError
from app.common.response import success
from app.common.serializers import format_dt
from app.database import get_db
from app.models.sys_user import SysUser
from app.schemas.common import PageResult, UserSummarySchema, build_page_meta

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def require_admin(current_user: SysUser) -> SysUser:
    if current_user.role != "admin":
        raise ForbiddenError("仅管理员可访问用户管理")
    return current_user


@router.get("")
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    require_admin(current_user)
    total = db.scalar(select(func.count()).select_from(SysUser)) or 0
    rows = db.scalars(
        select(SysUser).order_by(SysUser.id.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        UserSummarySchema(
            id=row.id,
            username=row.username,
            display_name=row.display_name,
            role=row.role,
            is_active=row.is_active,
            created_at=format_dt(row.created_at) or "",
            updated_at=format_dt(row.updated_at) or "",
        )
        for row in rows
    ]
    result = PageResult(
        items=items,
        meta=build_page_meta(page, page_size, total),
    )
    return success(data=result.model_dump())
