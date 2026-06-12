from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Runbook(Base):
    __tablename__ = "runbook"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    steps_json: Mapped[list] = mapped_column(JSON, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", name="runbook_risk_level"),
        nullable=False,
        default="low",
    )
    service_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    alert_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("draft", "published", name="runbook_status"),
        nullable=False,
        default="draft",
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )


class RunbookExecution(Base):
    __tablename__ = "runbook_execution"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    runbook_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("runbook.id", ondelete="RESTRICT"), nullable=False
    )
    incident_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incident.id", ondelete="CASCADE"), nullable=False
    )
    rca_result_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("rca_result.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "running",
            "completed",
            "failed",
            "cancelled",
            name="runbook_execution_status",
        ),
        nullable=False,
        default="pending",
    )
    triggered_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    step_results_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )

    runbook = relationship("Runbook", foreign_keys=[runbook_id])
    incident = relationship("Incident", foreign_keys=[incident_id])
