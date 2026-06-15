import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import ErrorResponse, OtpVerify, SifreSifirla, SifreSifirlamaIstek, Token, UserCreate, UserLogin, UserResponse, UserUpdate
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_mail,
)
from app.services.auth import hash_password
from app.services.otp import send_otp, verify_otp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_401 = {"model": ErrorResponse}
_500 = {"model": ErrorResponse}


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: _500},
    summary="Kayıt ol — OTP e-postaya gönderilir",
)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_mail(db, user_data.mail):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kayıtlı",
        )
    try:
        create_user(db, user_data)
    except SQLAlchemyError as e:
        logger.exception("Kullanıcı oluşturulurken veritabanı hatası: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu hatası, lütfen tekrar deneyin",
        )

    sent = await send_otp(user_data.mail)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doğrulama kodu gönderilemedi, lütfen tekrar deneyin",
        )

    return {"detail": "Kayıt başarılı, e-postanıza doğrulama kodu gönderildi"}


@router.post(
    "/verify-otp",
    response_model=Token,
    responses={401: _401, 500: _500},
    summary="Kayıt OTP doğrula — hesabı aktif et ve JWT döner",
)
async def verify_otp_endpoint(payload: OtpVerify, db: Session = Depends(get_db)):
    valid = await verify_otp(payload.mail, payload.otp)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doğrulama kodu hatalı veya süresi dolmuş",
        )

    user = get_user_by_mail(db, payload.mail)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
        )

    user.is_verified = True
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as e:
        logger.exception("Kullanıcı doğrulanırken hata: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu hatası, lütfen tekrar deneyin",
        )

    token = create_access_token(user.id)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=Token,
    responses={401: _401, 500: _500},
    summary="Giriş — e-posta + şifre ile direkt JWT döner",
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

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta adresiniz doğrulanmamış, lütfen kayıt e-postanızdaki kodu girin",
        )

    token = create_access_token(user.id)
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/sifre-sifirla/istek",
    responses={404: {"model": ErrorResponse}, 500: _500},
    summary="Şifre sıfırlama — OTP e-postaya gönderilir",
)
async def sifre_sifirla_istek(payload: SifreSifirlamaIstek, db: Session = Depends(get_db)):
    user = get_user_by_mail(db, payload.mail)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu e-posta ile kayıtlı kullanıcı bulunamadı",
        )

    sent = await send_otp(payload.mail)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doğrulama kodu gönderilemedi, lütfen tekrar deneyin",
        )

    return {"detail": "Şifre sıfırlama kodu e-posta adresinize gönderildi"}


@router.post(
    "/sifre-sifirla/dogrula",
    responses={401: _401, 500: _500},
    summary="OTP doğrula ve yeni şifre belirle",
)
async def sifre_sifirla_dogrula(payload: SifreSifirla, db: Session = Depends(get_db)):
    valid = await verify_otp(payload.mail, payload.otp)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doğrulama kodu hatalı veya süresi dolmuş",
        )

    user = get_user_by_mail(db, payload.mail)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
        )

    user.sifre_hash = hash_password(payload.yeni_sifre)
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.exception("Şifre güncellenirken hata: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu hatası, lütfen tekrar deneyin",
        )

    return {"detail": "Şifreniz başarıyla güncellendi, giriş yapabilirsiniz"}


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: _401},
)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    responses={401: _401, 500: _500},
    summary="Profil bilgilerini güncelle",
)
def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.isim is not None:
        current_user.isim = data.isim
    if data.soyisim is not None:
        current_user.soyisim = data.soyisim
    if data.cinsiyet is not None:
        current_user.cinsiyet = data.cinsiyet
    try:
        db.commit()
        db.refresh(current_user)
    except SQLAlchemyError as e:
        logger.exception("Profil güncellenirken hata: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sunucu hatası, lütfen tekrar deneyin",
        )
    return current_user
