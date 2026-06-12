"""Knowledge Base CRUD 与审核发布（阶段五 5.4）。"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.common.serializers import format_dt
from app.models.kb_article import KbArticle
from app.schemas.common import (
    KbArticleCreateRequest,
    KbArticleSchema,
    KbArticleUpdateRequest,
    PageResult,
    build_page_meta,
)


def kb_to_schema(row: KbArticle) -> KbArticleSchema:
    return KbArticleSchema(
        id=row.id,
        title=row.title,
        summary=row.summary,
        content=row.content,
        tags_text=row.tags_text,
        service=row.service,
        source_incident_id=row.source_incident_id,
        status=row.status,
        created_at=format_dt(row.created_at) or "",
        updated_at=format_dt(row.updated_at) or "",
    )


def _get_article_or_404(db: Session, article_id: int) -> KbArticle:
    row = db.get(KbArticle, article_id)
    if row is None:
        raise NotFoundError(message="KB 文章不存在", data={"kb_article_id": article_id})
    return row


def _require_admin(role: str) -> None:
    if role != "admin":
        raise ForbiddenError(message="需要管理员权限")


def list_kb_articles(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    service: str | None = None,
    keyword: str | None = None,
    source_incident_id: int | None = None,
) -> PageResult[KbArticleSchema]:
    filters = []
    if status:
        filters.append(KbArticle.status == status)
    if service:
        filters.append(KbArticle.service == service)
    if source_incident_id is not None:
        filters.append(KbArticle.source_incident_id == source_incident_id)
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                KbArticle.title.like(like),
                KbArticle.summary.like(like),
                KbArticle.tags_text.like(like),
            )
        )

    total = int(
        db.scalar(select(func.count()).select_from(KbArticle).where(*filters)) or 0
    )
    rows = db.scalars(
        select(KbArticle)
        .where(*filters)
        .order_by(KbArticle.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PageResult(
        items=[kb_to_schema(r) for r in rows],
        meta=build_page_meta(page, page_size, total),
    )


def get_kb_article(db: Session, article_id: int) -> KbArticleSchema:
    return kb_to_schema(_get_article_or_404(db, article_id))


def create_kb_article(
    db: Session,
    body: KbArticleCreateRequest,
    *,
    actor_role: str,
) -> KbArticleSchema:
    _require_admin(actor_role)
    row = KbArticle(
        title=body.title,
        summary=body.summary,
        content=body.content,
        tags_text=body.tags_text,
        service=body.service,
        source_incident_id=body.source_incident_id,
        status="draft",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return kb_to_schema(row)


def update_kb_article(
    db: Session,
    article_id: int,
    body: KbArticleUpdateRequest,
    *,
    actor_role: str,
) -> KbArticleSchema:
    _require_admin(actor_role)
    row = _get_article_or_404(db, article_id)

    if body.title is not None:
        row.title = body.title
    if body.summary is not None:
        row.summary = body.summary
    if body.content is not None:
        row.content = body.content
    if body.tags_text is not None:
        row.tags_text = body.tags_text
    if body.service is not None:
        row.service = body.service

    db.commit()
    db.refresh(row)
    return kb_to_schema(row)


def publish_kb_article(db: Session, article_id: int, *, actor_role: str) -> KbArticleSchema:
    _require_admin(actor_role)
    row = _get_article_or_404(db, article_id)
    if not row.content.strip():
        raise BadRequestError(message="正文为空，无法发布")
    row.status = "published"
    db.commit()
    db.refresh(row)
    return kb_to_schema(row)


def unpublish_kb_article(db: Session, article_id: int, *, actor_role: str) -> KbArticleSchema:
    _require_admin(actor_role)
    row = _get_article_or_404(db, article_id)
    row.status = "draft"
    db.commit()
    db.refresh(row)
    return kb_to_schema(row)


def delete_kb_article(db: Session, article_id: int, *, actor_role: str) -> None:
    _require_admin(actor_role)
    row = _get_article_or_404(db, article_id)
    db.delete(row)
    db.commit()
