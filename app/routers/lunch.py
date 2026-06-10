import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.mekan_onerisi import MekanOnerisi
from app.models.oy import Oy
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.lunch import (
    MekanListesiResponse,
    MekanOneriCreate,
    MekanOneriResponse,
    MekanOnerileriListesi,
    OneriKullanici,
    OyKullananKullanici,
    OyResponse,
    SonucMekan,
    SonuclarResponse,
)
from app.schemas.user import ErrorResponse
from app.services.lunch import mekan_listesi_getir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lunch", tags=["lunch"])

_401 = {"model": ErrorResponse}
_500 = {"model": ErrorResponse}


@router.get(
    "/mekanlar",
    response_model=MekanListesiResponse,
    responses={401: _401, 500: _500},
    summary="Yakın çevredeki yemek mekanlarını listele",
    description=(
        "Backendde tanımlı GPS koordinatına göre Gemini AI üzerinden "
        "öğle yemeği için uygun mekan listesini döndürür. Bearer token gereklidir."
    ),
)
async def get_mekanlar(current_user: User = Depends(get_current_user)):
    lat = settings.lunch_latitude
    lng = settings.lunch_longitude

    try:
        mekanlar = await mekan_listesi_getir(lat, lng)
    except ValueError as exc:
        logger.error("Mekan listesi alınamadı: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Beklenmeyen hata - mekan listesi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI servisine ulaşılamadı, lütfen tekrar deneyin",
        )

    return MekanListesiResponse(
        mekanlar=mekanlar,
        konum={"lat": lat, "lng": lng},
        toplam=len(mekanlar),
    )


@router.post(
    "/oner",
    response_model=MekanOneriResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: _401, 500: _500},
    summary="Yeni mekan öner",
    description="Kullanıcı kendi mekan önerisini ekler. Bearer token gereklidir.",
)
def mekan_oner(
    oneri: MekanOneriCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    yeni = MekanOnerisi(
        isim=oneri.isim,
        adres=oneri.adres,
        mutfak_turu=oneri.mutfak_turu,
        onerilen_by=current_user.id,
    )
    db.add(yeni)
    db.commit()
    db.refresh(yeni)

    return MekanOneriResponse(
        id=yeni.id,
        isim=yeni.isim,
        adres=yeni.adres,
        mutfak_turu=yeni.mutfak_turu,
        oneren=OneriKullanici(
            id=current_user.id,
            isim=current_user.isim,
            soyisim=current_user.soyisim,
        ),
        created_at=yeni.created_at,
    )


@router.get(
    "/oneriler",
    response_model=MekanOnerileriListesi,
    responses={401: _401},
    summary="Kullanıcı önerilerini listele",
    description="Tüm kullanıcıların önerdiği mekanları döndürür. Bearer token gereklidir.",
)
def get_oneriler(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    kayitlar = db.query(MekanOnerisi).order_by(MekanOnerisi.created_at.desc()).all()

    oy_sayilari = (
        db.query(Oy.mekan_id, func.count(Oy.id).label("sayi"))
        .group_by(Oy.mekan_id)
        .all()
    )
    oy_map = {row.mekan_id: row.sayi for row in oy_sayilari}

    benim_oylarim = {
        oy.mekan_id
        for oy in db.query(Oy).filter(Oy.kullanici_id == current_user.id).all()
    }

    oneriler = [
        MekanOneriResponse(
            id=k.id,
            isim=k.isim,
            adres=k.adres,
            mutfak_turu=k.mutfak_turu,
            oneren=OneriKullanici(
                id=k.kullanici.id,
                isim=k.kullanici.isim,
                soyisim=k.kullanici.soyisim,
            ),
            oy_sayisi=oy_map.get(k.id, 0),
            oy_kullandim=k.id in benim_oylarim,
            created_at=k.created_at,
        )
        for k in kayitlar
    ]

    return MekanOnerileriListesi(oneriler=oneriler, toplam=len(oneriler))


@router.post(
    "/oy/{mekan_id}",
    response_model=OyResponse,
    responses={401: _401, 404: {"model": ErrorResponse}},
    summary="Mekana oy ver veya geri al",
    description=(
        "Kullanıcı bir mekana oy verir. Zaten oy verdiyse oy geri alınır (toggle). "
        "Bearer token gereklidir."
    ),
)
def oy_ver(
    mekan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mekan = db.query(MekanOnerisi).filter(MekanOnerisi.id == mekan_id).first()
    if not mekan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mekan bulunamadı",
        )

    mevcut_oy = (
        db.query(Oy)
        .filter(Oy.kullanici_id == current_user.id, Oy.mekan_id == mekan_id)
        .first()
    )

    if mevcut_oy:
        db.delete(mevcut_oy)
        db.commit()
        oy_kullandim = False
    else:
        try:
            yeni_oy = Oy(kullanici_id=current_user.id, mekan_id=mekan_id)
            db.add(yeni_oy)
            db.commit()
            oy_kullandim = True
        except IntegrityError:
            db.rollback()
            oy_kullandim = True

    oy_sayisi = db.query(func.count(Oy.id)).filter(Oy.mekan_id == mekan_id).scalar()
    return OyResponse(mekan_id=mekan_id, oy_sayisi=oy_sayisi, oy_kullandim=oy_kullandim)


@router.get(
    "/sonuclar",
    response_model=SonuclarResponse,
    responses={401: _401},
    summary="Oy sonuçlarını listele",
    description=(
        "En çok oylanan mekanları sıralı döndürür. "
        "Oy kullananlar ve kullanmayanlar listesini içerir. Bearer token gereklidir."
    ),
)
def get_sonuclar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mekanlar = db.query(MekanOnerisi).all()
    tum_kullanicilar = db.query(User).all()

    oy_sayilari = (
        db.query(Oy.mekan_id, func.count(Oy.id).label("sayi"))
        .group_by(Oy.mekan_id)
        .all()
    )
    oy_map = {row.mekan_id: row.sayi for row in oy_sayilari}

    benim_oylarim = {
        oy.mekan_id
        for oy in db.query(Oy).filter(Oy.kullanici_id == current_user.id).all()
    }

    sirali = sorted(mekanlar, key=lambda m: oy_map.get(m.id, 0), reverse=True)

    sirali_mekanlar = [
        SonucMekan(
            sira=idx + 1,
            mekan_id=m.id,
            isim=m.isim,
            adres=m.adres,
            mutfak_turu=m.mutfak_turu,
            oneren=OneriKullanici(
                id=m.kullanici.id,
                isim=m.kullanici.isim,
                soyisim=m.kullanici.soyisim,
            ),
            oy_sayisi=oy_map.get(m.id, 0),
            oy_kullandim=m.id in benim_oylarim,
        )
        for idx, m in enumerate(sirali)
    ]

    oy_kullanan_ids = {oy.kullanici_id for oy in db.query(Oy).all()}

    oy_kullananlar = [
        OyKullananKullanici(
            id=oy.kullanici.id,
            isim=oy.kullanici.isim,
            soyisim=oy.kullanici.soyisim,
            oy_zamani=oy.created_at,
        )
        for oy in (
            db.query(Oy)
            .distinct(Oy.kullanici_id)
            .order_by(Oy.kullanici_id, Oy.created_at.desc())
            .all()
        )
    ]

    oy_kullanmayanlar = [
        OneriKullanici(id=u.id, isim=u.isim, soyisim=u.soyisim)
        for u in tum_kullanicilar
        if u.id not in oy_kullanan_ids
    ]

    return SonuclarResponse(
        sirali_mekanlar=sirali_mekanlar,
        oy_kullananlar=oy_kullananlar,
        oy_kullanmayanlar=oy_kullanmayanlar,
        toplam_katilimci=len(oy_kullanan_ids),
    )
