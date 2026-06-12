from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RcaResult(Base):
    __tablename__ = "rca_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incident.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "completed", "failed", name="rca_status"),
        nullable=False,
        default="pending",
    )
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    evidence_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggested_runbook_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    suggested_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    incident = relationship("Incident", foreign_keys=[incident_id])
