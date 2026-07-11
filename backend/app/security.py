import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import RevokedToken, User


settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    expires_at = datetime.utcnow() + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "exp": expires_at,
        "jti": secrets.token_urlsafe(24),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def issue_tokens(user: User) -> dict[str, str]:
    return {
        "access_token": create_token(str(user.id), "access", timedelta(minutes=settings.access_token_minutes)),
        "refresh_token": create_token(str(user.id), "refresh", timedelta(days=settings.refresh_token_days)),
    }


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub", "0"))
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_error
    except (JWTError, ValueError):
        raise credentials_error
    if not payload.get("jti") or db.query(RevokedToken).filter(RevokedToken.jti == payload["jti"]).first():
        raise credentials_error
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_error
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
