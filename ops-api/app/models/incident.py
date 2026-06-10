from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Incident(Base):
    __tablename__ = "incident"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            "open",
            "acknowledged",
            "investigating",
            "mitigated",
            "resolved",
            "closed",
            name="incident_status",
        ),
        nullable=False,
        default="open",
    )
    severity: Mapped[str] = mapped_column(
        Enum("critical", "high", "medium", "low", name="incident_severity"),
        nullable=False,
    )
    service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    primary_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    root_cause_preview: Mapped[str | None] = mapped_column(String(512), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("SysUser", foreign_keys=[owner_id])
