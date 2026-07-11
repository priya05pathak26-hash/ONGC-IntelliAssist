from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import RevokedToken, User
from app.schemas import TokenPair, UserCreate, UserLogin, UserOut
from app.security import get_current_user, hash_password, issue_tokens, oauth2_scheme, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role if payload.role in {"admin", "employee", "viewer"} else "employee",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        user = db.get(User, int(payload["sub"]))
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return issue_tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout", status_code=204)
def logout(token: str = Depends(oauth2_scheme), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalidate the access token server-side as well as in the browser."""
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    jti = payload.get("jti")
    if jti and not db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        db.add(RevokedToken(jti=jti, expires_at=datetime.utcfromtimestamp(payload["exp"])))
        db.commit()


@router.post("/forgot-password")
def forgot_password(email: str):
    return {"message": "If the account exists, contact the administrator to reset access securely."}
