"""Runbook CRUD、执行与采纳率统计（阶段四 4.2 / 4.5 / 4.6）。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.common.serializers import format_dt
from app.incidents.service import _add_timeline, _get_incident_or_404
from app.models.rca_result import RcaResult
from app.models.runbook import Runbook, RunbookExecution
from app.runbook.runbook_executor import execute_runbook_steps
from app.schemas.common import (
    PageResult,
    RunbookAdoptionStatsSchema,
    RunbookCreateRequest,
    RunbookExecutionSchema,
    RunbookExecutionStartRequest,
    RunbookSchema,
    RunbookUpdateRequest,
    build_page_meta,
)


def runbook_to_schema(row: Runbook) -> RunbookSchema:
    return RunbookSchema(
        id=row.id,
        title=row.title,
        description=row.description,
        steps=row.steps_json or [],
        risk_level=row.risk_level,
        service_tags=row.service_tags or [],
        alert_names=row.alert_names or [],
        status=row.status,
        created_at=format_dt(row.created_at) or "",
        updated_at=format_dt(row.updated_at) or "",
    )


def execution_to_schema(row: RunbookExecution) -> RunbookExecutionSchema:
    runbook_title = row.runbook.title if row.runbook else None
    return RunbookExecutionSchema(
        id=row.id,
        runbook_id=row.runbook_id,
        runbook_title=runbook_title,
        incident_id=row.incident_id,
        rca_result_id=row.rca_result_id,
        status=row.status,
        step_results=row.step_results_json or [],
        error_message=row.error_message,
        started_at=format_dt(row.started_at),
        completed_at=format_dt(row.completed_at),
        created_at=format_dt(row.created_at) or "",
    )


def _get_runbook_or_404(db: Session, runbook_id: int) -> Runbook:
    row = db.get(Runbook, runbook_id)
    if row is None:
        raise NotFoundError(message="Runbook 不存在", data={"runbook_id": runbook_id})
    return row


def _require_admin(role: str) -> None:
    if role != "admin":
        raise ForbiddenError(message="需要管理员权限")


def list_runbooks(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    service: str | None = None,
    published_only: bool = False,
) -> PageResult[RunbookSchema]:
    stmt = select(Runbook)
    count_stmt = select(func.count()).select_from(Runbook)

    if published_only:
        stmt = stmt.where(Runbook.status == "published")
        count_stmt = count_stmt.where(Runbook.status == "published")
    elif status:
        stmt = stmt.where(Runbook.status == status)
        count_stmt = count_stmt.where(Runbook.status == status)
    if service:
        tag_filter = func.json_contains(Runbook.service_tags, f'"{service}"')
        stmt = stmt.where(tag_filter)
        count_stmt = count_stmt.where(tag_filter)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(Runbook.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PageResult(
        items=[runbook_to_schema(r) for r in rows],
        meta=build_page_meta(page, page_size, total),
    )


def get_runbook(db: Session, runbook_id: int) -> RunbookSchema:
    return runbook_to_schema(_get_runbook_or_404(db, runbook_id))


def create_runbook(
    db: Session,
    body: RunbookCreateRequest,
    *,
    actor_id: int | None,
    actor_role: str,
) -> RunbookSchema:
    _require_admin(actor_role)
    if not body.steps:
        raise BadRequestError(message="steps 不能为空")

    row = Runbook(
        title=body.title,
        description=body.description,
        steps_json=body.steps,
        risk_level=body.risk_level,
        service_tags=body.service_tags,
        alert_names=body.alert_names,
        status="draft",
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return runbook_to_schema(row)


def update_runbook(
    db: Session,
    runbook_id: int,
    body: RunbookUpdateRequest,
    *,
    actor_id: int | None,
    actor_role: str,
) -> RunbookSchema:
    _require_admin(actor_role)
    row = _get_runbook_or_404(db, runbook_id)

    if body.title is not None:
        row.title = body.title
    if body.description is not None:
        row.description = body.description
    if body.steps is not None:
        if not body.steps:
            raise BadRequestError(message="steps 不能为空")
        row.steps_json = body.steps
    if body.risk_level is not None:
        row.risk_level = body.risk_level
    if body.service_tags is not None:
        row.service_tags = body.service_tags
    if body.alert_names is not None:
        row.alert_names = body.alert_names

    row.updated_by = actor_id
    db.commit()
    db.refresh(row)
    return runbook_to_schema(row)


def publish_runbook(
    db: Session,
    runbook_id: int,
    *,
    actor_id: int | None,
    actor_role: str,
) -> RunbookSchema:
    _require_admin(actor_role)
    row = _get_runbook_or_404(db, runbook_id)
    if not row.steps_json:
        raise BadRequestError(message="无法发布空步骤 Runbook")
    row.status = "published"
    row.updated_by = actor_id
    db.commit()
    db.refresh(row)
    return runbook_to_schema(row)


def unpublish_runbook(
    db: Session,
    runbook_id: int,
    *,
    actor_id: int | None,
    actor_role: str,
) -> RunbookSchema:
    _require_admin(actor_role)
    row = _get_runbook_or_404(db, runbook_id)
    row.status = "draft"
    row.updated_by = actor_id
    db.commit()
    db.refresh(row)
    return runbook_to_schema(row)


def delete_runbook(
    db: Session,
    runbook_id: int,
    *,
    actor_role: str,
) -> None:
    _require_admin(actor_role)
    row = _get_runbook_or_404(db, runbook_id)
    if row.status == "published":
        raise BadRequestError(message="已发布 Runbook 请先下架再删除")
    db.delete(row)
    db.commit()


def list_runbook_executions(
    db: Session,
    incident_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> PageResult[RunbookExecutionSchema]:
    _get_incident_or_404(db, incident_id)
    base = select(RunbookExecution).where(RunbookExecution.incident_id == incident_id)
    total = int(
        db.scalar(select(func.count()).select_from(base.subquery())) or 0
    )
    rows = db.scalars(
        base.order_by(RunbookExecution.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    for row in rows:
        db.refresh(row, attribute_names=["runbook"])
    return PageResult(
        items=[execution_to_schema(r) for r in rows],
        meta=build_page_meta(page, page_size, total),
    )


def start_runbook_execution(
    db: Session,
    incident_id: int,
    body: RunbookExecutionStartRequest,
    *,
    actor_id: int | None,
) -> RunbookExecutionSchema:
    incident = _get_incident_or_404(db, incident_id)
    runbook = _get_runbook_or_404(db, body.runbook_id)

    if runbook.status != "published":
        raise BadRequestError(message="只能执行已发布的 Runbook")
    if not body.confirmed:
        raise BadRequestError(message="半自动处置需 confirmed=true 人工确认后执行")

    if body.rca_result_id is not None:
        rca = db.get(RcaResult, body.rca_result_id)
        if rca is None or rca.incident_id != incident_id:
            raise BadRequestError(message="rca_result_id 与 Incident 不匹配")

    execution = RunbookExecution(
        runbook_id=runbook.id,
        incident_id=incident_id,
        rca_result_id=body.rca_result_id,
        status="running",
        triggered_by=actor_id,
        started_at=datetime.now(),
    )
    db.add(execution)
    db.flush()

    _add_timeline(
        db,
        incident_id,
        event_type="system",
        content=f"开始执行 Runbook「{runbook.title}」",
        actor_type="user",
        actor_id=actor_id,
        metadata={
            "runbook_id": runbook.id,
            "runbook_execution_id": execution.id,
            "rca_result_id": body.rca_result_id,
        },
    )
    db.commit()

    step_results, success, err = execute_runbook_steps(runbook.steps_json or [])
    execution.step_results_json = step_results
    execution.completed_at = datetime.now()

    manual_steps = [
        s for s in step_results if s.get("action_type") == "manual" or s.get("status") == "manual"
    ]
    if success:
        execution.status = "completed"
        timeline_msg = f"Runbook「{runbook.title}」HTTP 步骤执行完成"
        if manual_steps:
            titles = "、".join(str(s.get("title") or "人工步骤") for s in manual_steps[:3])
            timeline_msg += f"；待人工：{titles}"
    else:
        execution.status = "failed"
        execution.error_message = (err or "执行失败")[:512]
        timeline_msg = f"Runbook「{runbook.title}」执行失败：{execution.error_message}"

    _add_timeline(
        db,
        incident_id,
        event_type="system",
        content=timeline_msg,
        actor_type="system",
        actor_id=actor_id,
        metadata={
            "runbook_id": runbook.id,
            "runbook_execution_id": execution.id,
            "status": execution.status,
            "step_results": step_results,
        },
    )

    if success and incident.status in ("investigating", "acknowledged", "open"):
        incident.status = "mitigated"

    db.commit()
    db.refresh(execution, attribute_names=["runbook"])
    return execution_to_schema(execution)


def get_adoption_stats(db: Session) -> RunbookAdoptionStatsSchema:
    """RCA 推荐 Runbook 被实际执行的比例（阶段四 4.6）。"""
    rca_rows = db.scalars(
        select(RcaResult).where(
            RcaResult.status == "completed",
            RcaResult.suggested_runbook_ids.isnot(None),
        )
    ).all()

    recommended_incidents = 0
    adopted_incidents = 0
    total_executions = int(
        db.scalar(select(func.count()).select_from(RunbookExecution)) or 0
    )
    successful_executions = int(
        db.scalar(
            select(func.count()).select_from(RunbookExecution).where(
                RunbookExecution.status == "completed"
            )
        )
        or 0
    )

    for rca in rca_rows:
        ids = rca.suggested_runbook_ids or []
        if not ids:
            continue
        recommended_incidents += 1
        executed = db.scalar(
            select(func.count())
            .select_from(RunbookExecution)
            .where(
                RunbookExecution.incident_id == rca.incident_id,
                RunbookExecution.rca_result_id == rca.id,
                RunbookExecution.runbook_id.in_(ids),
                RunbookExecution.status.in_(("completed", "failed", "running")),
            )
        )
        if executed and int(executed) > 0:
            adopted_incidents += 1

    adoption_rate = 0.0
    if recommended_incidents > 0:
        adoption_rate = round(adopted_incidents / recommended_incidents, 4)

    success_rate = 0.0
    if total_executions > 0:
        success_rate = round(successful_executions / total_executions, 4)

    return RunbookAdoptionStatsSchema(
        recommended_rca_count=recommended_incidents,
        adopted_rca_count=adopted_incidents,
        adoption_rate=adoption_rate,
        total_executions=total_executions,
        successful_executions=successful_executions,
        execution_success_rate=success_rate,
    )
