from datetime import timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from synchro.core.config import get_settings
from synchro.core.timeutils import utcnow

_settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _encode_token(subject: str, token_type: str, lifetime: timedelta) -> str:
    now = utcnow()
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def create_access_token(user_id: int) -> str:
    return _encode_token(
        str(user_id), "access", timedelta(minutes=_settings.jwt_access_token_expire_minutes)
    )


def create_refresh_token(
    user_id: int, family_id: str, jti: str | None = None
) -> tuple[str, str]:
    now = utcnow()
    token_jti = jti or uuid4().hex
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=_settings.jwt_refresh_token_expire_days),
        "jti": token_jti,
        "fam": family_id,
    }
    token = jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)
    return token, token_jti


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _settings.jwt_secret_key, algorithms=[_settings.jwt_algorithm])
