import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import ErrorResponse, Token, UserCreate, UserLogin, UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_mail,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_401 = {"model": ErrorResponse}
_500 = {"model": ErrorResponse}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: _500},
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_mail(db, user_data.mail):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kayıtlı",
        )
    try:
        return create_user(db, user_data)
    except SQLAlchemyError as e:
        logger.exception("Kullanıcı oluşturulurken veritabanı hatası: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu hatası, lütfen tekrar deneyin",
        )


@router.post(
    "/login",
    response_model=Token,
    responses={401: _401, 500: _500},
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, credentials.mail, credentials.sifre)
    except SQLAlchemyError as e:
        logger.exception("Giriş sırasında veritabanı hatası: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu hatası, lütfen tekrar deneyin",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya şifre hatalı",
        )

    token = create_access_token(user.id)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: _401},
)
def me(current_user: User = Depends(get_current_user)):
    return current_user
