from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, settings
from app.models.user import User
from app.schemas.user import UserCreate


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user.id),
        "exp": expire,
        "mail": user.mail,
        "isim": user.isim,
        "soyisim": user.soyisim,
        "cinsiyet": user.cinsiyet,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (JWTError, ValueError):
        return None


def get_user_by_mail(db: Session, mail: str) -> User | None:
    return db.query(User).filter(User.mail == mail).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    user = User(
        isim=user_data.isim,
        soyisim=user_data.soyisim,
        mail=user_data.mail,
        cinsiyet=user_data.cinsiyet,
        sifre_hash=hash_password(user_data.sifre),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, mail: str, password: str) -> User | None:
    user = get_user_by_mail(db, mail)
    if not user or not verify_password(password, user.sifre_hash):
        return None
    return user
