from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.response import success
from app.database import get_db
from app.incidents.service import (
    create_incident,
    create_timeline_event,
    get_incident_detail,
    list_incidents,
    list_timeline,
    patch_incident,
)
from app.models.sys_user import SysUser
from app.schemas.common import IncidentCreateRequest, IncidentPatchRequest, TimelineCreateRequest

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


@router.get("")
def get_incidents(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    severity: str | None = None,
    owner_id: int | None = None,
    service: str | None = None,
    keyword: str | None = None,
):
    result = list_incidents(
        db,
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
        owner_id=owner_id,
        service=service,
        keyword=keyword,
    )
    return success(data=result.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def post_incident(
    body: IncidentCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    incident = create_incident(db, body, actor_id=current_user.id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success(data=incident.model_dump()),
    )


@router.get("/{incident_id}")
def get_incident(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    detail = get_incident_detail(db, incident_id)
    return success(data=detail.model_dump())


@router.patch("/{incident_id}")
def patch_incident_endpoint(
    incident_id: int,
    body: IncidentPatchRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    incident = patch_incident(db, incident_id, body, actor_id=current_user.id)
    return success(data=incident.model_dump())


timeline_router = APIRouter(prefix="/api/v1/incidents/{incident_id}/timeline", tags=["Timeline"])


@timeline_router.get("")
def get_timeline(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = list_timeline(db, incident_id, page=page, page_size=page_size)
    return success(data=result.model_dump())


@timeline_router.post("", status_code=status.HTTP_201_CREATED)
def post_timeline(
    incident_id: int,
    body: TimelineCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    event = create_timeline_event(db, incident_id, body, actor_id=current_user.id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success(data=event.model_dump()),
    )
