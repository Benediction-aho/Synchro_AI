import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from synchro.core.timeutils import utcnow
from synchro.db.base import Base, str_enum


class AccountType(str, enum.Enum):
    DEMO = "demo"
    LIVE = "live"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(16), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    devices = relationship("Device", back_populates="user")
    accounts = relationship("Account", back_populates="user")
    api_credentials = relationship("ApiCredential", back_populates="user")
    alerts = relationship("Alert", back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    device_name: Mapped[str] = mapped_column(String(128))
    os: Mapped[str] = mapped_column(String(64))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="devices")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), default="main")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="accounts")
    configuration = relationship("Configuration", back_populates="account", uselist=False)
    api_credentials = relationship("ApiCredential", back_populates="account")
    trades = relationship("Trade", back_populates="account")
    signals = relationship("Signal", back_populates="account")
    equity_snapshots = relationship("EquitySnapshot", back_populates="account")


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), index=True)
    deriv_token_encrypted: Mapped[str | None] = mapped_column(Text)
    broker_type: Mapped[str] = mapped_column(String(32), default="deriv")
    account_login: Mapped[str | None] = mapped_column(String(64))
    account_type: Mapped[AccountType] = mapped_column(str_enum(AccountType), default=AccountType.DEMO)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="api_credentials")
    account = relationship("Account", back_populates="api_credentials")
