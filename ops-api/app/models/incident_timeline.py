from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IncidentTimeline(Base):
    __tablename__ = "incident_timeline"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incident.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        Enum(
            "status_change",
            "assignment",
            "severity_change",
            "note",
            "alert_merged",
            "system",
            name="timeline_event_type",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(
        Enum("user", "system", name="actor_type"),
        nullable=False,
        default="system",
    )
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )

    actor = relationship("SysUser", foreign_keys=[actor_id])
