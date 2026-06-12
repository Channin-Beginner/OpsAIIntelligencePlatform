from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.response import success
from app.database import get_db
from app.kb.service import (
    create_kb_article,
    delete_kb_article,
    get_kb_article,
    list_kb_articles,
    publish_kb_article,
    unpublish_kb_article,
    update_kb_article,
)
from app.models.sys_user import SysUser
from app.schemas.common import KbArticleCreateRequest, KbArticleUpdateRequest

router = APIRouter(prefix="/api/v1/kb/articles", tags=["Knowledge Base"])


@router.get("")
def get_kb_articles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    service: str | None = None,
    keyword: str | None = None,
    source_incident_id: int | None = None,
):
    result = list_kb_articles(
        db,
        page=page,
        page_size=page_size,
        status=status,
        service=service,
        keyword=keyword,
        source_incident_id=source_incident_id,
    )
    return success(data=result.model_dump())


@router.get("/{article_id}")
def get_kb_article_detail(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = get_kb_article(db, article_id)
    return success(data=row.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
def post_kb_article(
    body: KbArticleCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = create_kb_article(db, body, actor_role=current_user.role)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=success(data=row.model_dump()),
    )


@router.patch("/{article_id}")
def patch_kb_article(
    article_id: int,
    body: KbArticleUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = update_kb_article(
        db, article_id, body, actor_role=current_user.role
    )
    return success(data=row.model_dump())


@router.post("/{article_id}/publish")
def post_publish_kb_article(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = publish_kb_article(db, article_id, actor_role=current_user.role)
    return success(data=row.model_dump())


@router.post("/{article_id}/unpublish")
def post_unpublish_kb_article(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    row = unpublish_kb_article(db, article_id, actor_role=current_user.role)
    return success(data=row.model_dump())


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kb_article_route(
    article_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[SysUser, Depends(get_current_user)],
):
    delete_kb_article(db, article_id, actor_role=current_user.role)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
