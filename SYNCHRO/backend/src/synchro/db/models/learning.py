from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from synchro.core.timeutils import utcnow
from synchro.db.base import Base, json_type


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), index=True)
    features: Mapped[dict] = mapped_column(json_type(), default=dict)
    hmm_state: Mapped[str | None] = mapped_column(String(32))
    session: Mapped[str | None] = mapped_column(String(32))
    outcome: Mapped[str | None] = mapped_column(String(32))
    is_win: Mapped[bool | None] = mapped_column(Boolean)

    trade = relationship("Trade", back_populates="patterns")


class QValue(Base):
    __tablename__ = "q_values"

    state_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), primary_key=True)
    q_value: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True)
    params: Mapped[dict] = mapped_column(json_type(), default=dict)
    backtest_metrics: Mapped[dict] = mapped_column(json_type(), default=dict)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)


class EvolutionLog(Base):
    __tablename__ = "evolution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_date: Mapped[date] = mapped_column(Date, index=True)
    variations_tested: Mapped[int] = mapped_column(default=0)
    winner: Mapped[str | None] = mapped_column(String(255))
    improvement_pct: Mapped[float | None] = mapped_column(Float)
    demo_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
