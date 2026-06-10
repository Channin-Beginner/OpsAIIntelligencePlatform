from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlertEvent(Base):
    __tablename__ = "alert_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="alertmanager")
    status: Mapped[str] = mapped_column(
        Enum("firing", "resolved", name="alert_status"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum("critical", "high", "medium", "low", name="alert_severity"),
        nullable=False,
        default="medium",
    )
    alertname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    annotations_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
