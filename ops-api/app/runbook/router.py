from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.response import success
from app.database import get_db
from app.models.sys_user import SysUser
from app.runbook.service import (
    create_runbook,
    delete_runbook,
    get_adoption_stats,
    get_runbook,
    list_runbook_executions,
    list_runbooks,
    publish_runbook,
    start_runbook_execution,
    unpublish_runbook,
    update_runbook,
)
from app.schemas.common import RunbookCreateRequest, RunbookExecutionStartRequest, RunbookUpdateRequest

router = APIRouter(prefix="/api/v1/runbooks", tags=["Runbooks"])


@router.get("")
def get_runbooks(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    service: str | None = None,
    published_only: bool = False,
):
    result = list_runbooks(
        db,
        page=page,
        page_size=page_size,
        status=status,
        service=service,
        published_only=published_only,
    )
    return success(data=result.model_dump())


@router.get("/stats/adoption")
def get_runbook_adoption_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    stats = get_adoption_stats(db)
    return success(data=stats.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def post_runbook(
    body: RunbookCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = create_runbook(
        db,
        body,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success(data=row.model_dump()),
    )


@router.get("/{runbook_id}")
def get_runbook_detail(
    runbook_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = get_runbook(db, runbook_id)
    return success(data=row.model_dump())


@router.patch("/{runbook_id}")
def patch_runbook(
    runbook_id: int,
    body: RunbookUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = update_runbook(
        db,
        runbook_id,
        body,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    return success(data=row.model_dump())


@router.post("/{runbook_id}/publish")
def post_runbook_publish(
    runbook_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = publish_runbook(
        db,
        runbook_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    return success(data=row.model_dump())


@router.post("/{runbook_id}/unpublish")
def post_runbook_unpublish(
    runbook_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = unpublish_runbook(
        db,
        runbook_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    return success(data=row.model_dump())


@router.delete("/{runbook_id}")
def delete_runbook_endpoint(
    runbook_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    delete_runbook(db, runbook_id, actor_role=current_user.role)
    return success(data=None)


execution_router = APIRouter(
    prefix="/api/v1/incidents/{incident_id}/runbook-executions",
    tags=["Runbook Executions"],
)


@execution_router.get("")
def get_incident_runbook_executions(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = list_runbook_executions(db, incident_id, page=page, page_size=page_size)
    return success(data=result.model_dump())


@execution_router.post("", status_code=status.HTTP_201_CREATED)
def post_incident_runbook_execution(
    incident_id: int,
    body: RunbookExecutionStartRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    result = start_runbook_execution(
        db,
        incident_id,
        body,
        actor_id=current_user.id,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success(data=result.model_dump()),
    )
