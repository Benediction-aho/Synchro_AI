import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from synchro.core.timeutils import utcnow
from synchro.db.base import Base, json_type, str_enum


class AlertType(str, enum.Enum):
    APPROVAL = "approval"
    CRISIS = "crisis"
    INFO = "info"


class AlertResponse(str, enum.Enum):
    YES = "yes"
    NO = "no"
    TIMEOUT = "timeout"


class ActorType(str, enum.Enum):
    AGENT = "agent"
    HUMAN = "human"
    SYSTEM = "system"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[AlertType] = mapped_column(str_enum(AlertType))
    payload: Mapped[dict] = mapped_column(json_type(), default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response: Mapped[AlertResponse | None] = mapped_column(str_enum(AlertResponse))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[ActorType] = mapped_column(str_enum(ActorType))
    action: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
