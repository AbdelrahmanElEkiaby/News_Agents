from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import UserDB
from app.services.user_service import get_user_by_email, get_user_by_id

password_hash = PasswordHash.recommended()
dummy_password_hash = password_hash.hash("not-a-real-user-password")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def authenticate_user(db: Session, email: str, password: str) -> UserDB | None:
    user = get_user_by_email(db, email.strip().lower())

    if user is None or user.hashed_password is None:
        password_hash.verify(password, dummy_password_hash)
        return None

    try:
        password_is_valid = password_hash.verify(password, user.hashed_password)
    except UnknownHashError:
        return None

    if not password_is_valid:
        return None

    return user


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserDB:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise credentials_error

    user = get_user_by_id(db, user_id)

    if user is None or user.hashed_password is None:
        raise credentials_error

    return user
