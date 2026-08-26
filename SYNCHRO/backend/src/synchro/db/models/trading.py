import enum
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from synchro.core.timeutils import utcnow
from synchro.db.base import Base, json_type, str_enum


class TradeDirection(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    BREAKEVEN = "be"
    TRAILING = "trailing"
    CLOSED = "closed"


class SignalDecision(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class Configuration(Base):
    __tablename__ = "configurations"
    __table_args__ = (CheckConstraint("risk_phase >= 0 AND risk_phase <= 5", name="risk_phase_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True, index=True)
    allocated_capital: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    active_markets: Mapped[list] = mapped_column(json_type(), default=list)
    risk_phase: Mapped[int] = mapped_column(default=0)
    min_score: Mapped[int] = mapped_column(default=5)
    demo_lock_until: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    account = relationship("Account", back_populates="configuration")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (Index("ix_trades_account_id_opened_at", "account_id", "opened_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    symbol: Mapped[str] = mapped_column(String(32))
    direction: Mapped[TradeDirection] = mapped_column(str_enum(TradeDirection))
    entry_price: Mapped[float | None] = mapped_column(Numeric(18, 8))
    exit_price: Mapped[float | None] = mapped_column(Numeric(18, 8))
    sl_initial: Mapped[float | None] = mapped_column(Numeric(18, 8))
    sl_current: Mapped[float | None] = mapped_column(Numeric(18, 8))
    tp: Mapped[float | None] = mapped_column(Numeric(18, 8))
    lots: Mapped[float] = mapped_column(Numeric(18, 2))
    pnl: Mapped[float | None] = mapped_column(Numeric(18, 2))
    status: Mapped[TradeStatus] = mapped_column(str_enum(TradeStatus), default=TradeStatus.OPEN)
    score_components: Mapped[dict] = mapped_column(json_type(), default=dict)
    filters_snapshot: Mapped[dict] = mapped_column(json_type(), default=dict)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account = relationship("Account", back_populates="trades")
    patterns = relationship("Pattern", back_populates="trade")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    apex_layer_results: Mapped[dict] = mapped_column(json_type(), default=dict)
    decision: Mapped[SignalDecision] = mapped_column(str_enum(SignalDecision))
    reason_text: Mapped[str | None] = mapped_column(String(512))

    account = relationship("Account", back_populates="signals")


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, default=utcnow)
    balance: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    equity: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    daily_pnl: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    account = relationship("Account", back_populates="equity_snapshots")
