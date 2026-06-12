from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IncidentFeedback(Base):
    __tablename__ = "incident_feedback"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("incident.id", ondelete="CASCADE"), nullable=False
    )
    rca_result_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("rca_result.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    verdict: Mapped[str] = mapped_column(
        Enum("accept", "reject", name="feedback_verdict"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )

    incident = relationship("Incident", foreign_keys=[incident_id])
    rca_result = relationship("RcaResult", foreign_keys=[rca_result_id])
    user = relationship("SysUser", foreign_keys=[user_id])
