from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdsAlertDaily(Base):
    __tablename__ = "ads_alert_daily"

    stat_date: Mapped[date] = mapped_column(Date, primary_key=True)
    raw_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alertmanager_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grafana_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )


class AdsMttrDaily(Base):
    __tablename__ = "ads_mttr_daily"

    stat_date: Mapped[date] = mapped_column(Date, primary_key=True)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mttr_avg_minutes: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    mttr_p50_minutes: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )


class AdsAgentQuality(Base):
    __tablename__ = "ads_agent_quality"

    stat_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rca_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rca_accept_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rca_accept_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    runbook_exec_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runbook_exec_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runbook_success_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    kb_published_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now()
    )
