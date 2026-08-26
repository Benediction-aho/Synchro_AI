from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from synchro.core.config import get_settings
from synchro.core.login_guard import LoginGuard
from synchro.core.rate_limit import SlidingWindowLimiter, enforce
from synchro.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from synchro.core.token_registry import RegistryStatus, TokenRegistry
from synchro.db.models.user import User
from synchro.db.session import get_db
from synchro.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    Token,
    TokenWithUser,
    UserCreate,
    UserRead,
)

_settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=True)

_limiter = SlidingWindowLimiter()
_login_guard = LoginGuard(
    max_failures=_settings.login_max_failures,
    base_lock_seconds=_settings.login_base_lock_seconds,
    max_lock_seconds=_settings.login_max_lock_seconds,
)
_registry = TokenRegistry()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _issue_pair(user_id: int, family_id: str | None = None) -> tuple[Token, str]:
    family = family_id or uuid4().hex
    refresh_token, jti = create_refresh_token(user_id, family)
    _registry.register(user_id, family, jti)
    token = Token(access_token=create_access_token(user_id), refresh_token=refresh_token)
    return token, family


def _user_from_payload(payload: dict, db: Session) -> User:
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    return _user_from_payload(payload, db)


@router.post("/register", response_model=TokenWithUser, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, request: Request, db: Session = Depends(get_db)) -> TokenWithUser:
    enforce(_limiter, f"register:{_client_ip(request)}", _settings.rate_limit_register_per_hour, 3600)
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    pair, family = _issue_pair(user.id)
    return TokenWithUser(**pair.model_dump(), user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    ip = _client_ip(request)
    enforce(_limiter, f"login-ip:{ip}", _settings.rate_limit_login_per_window, _settings.rate_limit_window_seconds)
    email_key = f"login-email:{body.email.lower()}"
    enforce(_limiter, f"login-attempt:{email_key}", 10, _settings.rate_limit_window_seconds)
    _login_guard.check(email_key)

    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        _login_guard.record_failure(email_key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    _login_guard.reset(email_key)
    pair, _family = _issue_pair(user.id)
    return pair


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    enforce(_limiter, f"refresh:{_client_ip(request)}", 60, _settings.rate_limit_window_seconds)
    try:
        payload = decode_token(body.refresh_token)
    except PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        ) from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    try:
        user_id = int(payload["sub"])
        family_id = str(payload.get("fam", ""))
        presented_jti = str(payload.get("jti", ""))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims") from exc
    if not family_id or not presented_jti:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    new_jti = uuid4().hex
    outcome = _registry.exchange(family_id, presented_jti, new_jti)
    if outcome == RegistryStatus.REUSED:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected; session revoked",
        )
    if outcome == RegistryStatus.UNKNOWN:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Unknown session; log in again")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    refresh_token, stored_jti = create_refresh_token(user.id, family_id, jti=new_jti)
    return Token(access_token=create_access_token(user.id), refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest) -> None:
    try:
        payload = decode_token(body.refresh_token)
    except PyJWTError:
        return None
    if payload.get("type") == "refresh":
        family_id = str(payload.get("fam", ""))
        if family_id:
            _registry.kill_family(family_id)
    return None


@router.post("/change-password", response_model=Token)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Token:
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect current password")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    _registry.kill_all_for_user(current_user.id)
    pair, _family = _issue_pair(current_user.id)
    return pair


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
