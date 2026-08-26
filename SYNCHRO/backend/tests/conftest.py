import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import synchro.db.models  # noqa: F401
from synchro.db.base import Base
from synchro.db.session import get_db
from synchro.services.api_gateway.main import app

# Ensure TELEGRAM_BOT_TOKEN is set for tests BEFORE any settings are loaded
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "8729665957:AAESaelH61CZ7uubZq4nMQmJrfiweZ_Qsy8")

# Clear any cached settings
import synchro.core.config as config_module
if hasattr(config_module.get_settings, "cache_clear"):
    config_module.get_settings.cache_clear()

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    with TestClient(app) as c:
        yield c
