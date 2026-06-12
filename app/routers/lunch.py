import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache import mekan_cache
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.lunch_session import LunchSession, SessionDurum
from sqlalchemy import desc
from app.models.mekan_onerisi import MekanOnerisi
from app.models.oy import Oy
from app.models.user import User
from app.schemas.lunch import (
    GecmisResponse,
    GecmisSonuc,
    MekanListesiResponse,
    MekanOneriCreate,
    MekanOneriResponse,
    MekanOnerileriListesi,
    OneriKullanici,
    OyKullananKullanici,
    OyResponse,
    SessionDurumResponse,
    SonucMekan,
    SonuclarResponse,
)
from app.schemas.user import ErrorResponse
from app.services.lunch import mekan_listesi_getir
from app.services.session import get_aktif_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lunch", tags=["lunch"])

_401 = {"model": ErrorResponse}
_500 = {"model": ErrorResponse}


def _get_aktif_session_or_400(db: Session) -> LunchSession:
    """Aktif session yoksa 400 fırlatır."""
    session = get_aktif_session(db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aktif oturum yok, öneri kabul edilmiyor",
        )
    return session


@router.get(
    "/mekanlar",
    response_model=MekanListesiResponse,
    responses={401: _401, 500: _500},
    summary="Yakın çevredeki yemek mekanlarını listele",
)
async def get_mekanlar(
    lat: float = settings.lunch_latitude,
    lng: float = settings.lunch_longitude,
    current_user: User = Depends(get_current_user),
):
    cache_key = f"mekanlar:{lat}:{lng}"

    cached = await mekan_cache.get(cache_key)
    if cached is not None:
        return cached

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

    result = MekanListesiResponse(
        mekanlar=mekanlar,
        konum={"lat": lat, "lng": lng},
        toplam=len(mekanlar),
    )
    await mekan_cache.set(cache_key, result)
    return result


@router.post(
    "/oner",
    response_model=MekanOneriResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 401: _401},
    summary="Yeni mekan öner",
)
def mekan_oner(
    oneri: MekanOneriCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    aktif_session = _get_aktif_session_or_400(db)

    duplicate = db.execute(
        select(MekanOnerisi).where(
            MekanOnerisi.session_id == aktif_session.id,
            func.lower(MekanOnerisi.isim) == oneri.isim.lower().strip(),
        )
    ).scalar_one_or_none()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu mekan bugün zaten önerilmiş",
        )

    yeni = MekanOnerisi(
        session_id=aktif_session.id,
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
    responses={400: {"model": ErrorResponse}, 401: _401},
    summary="Bugünkü önerileri listele",
)
def get_oneriler(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    aktif_session = _get_aktif_session_or_400(db)

    oy_sayisi_subq = (
        select(Oy.mekan_id, func.count(Oy.id).label("sayi"))
        .where(Oy.session_id == aktif_session.id)
        .group_by(Oy.mekan_id)
        .subquery()
    )

    rows = (
        db.query(
            MekanOnerisi,
            func.coalesce(oy_sayisi_subq.c.sayi, 0).label("oy_sayisi"),
        )
        .filter(MekanOnerisi.session_id == aktif_session.id)
        .outerjoin(oy_sayisi_subq, MekanOnerisi.id == oy_sayisi_subq.c.mekan_id)
        .order_by(MekanOnerisi.created_at.desc())
        .all()
    )

    benim_oylarim = {
        row.mekan_id
        for row in db.execute(
            select(Oy.mekan_id).where(
                Oy.kullanici_id == current_user.id,
                Oy.session_id == aktif_session.id,
            )
        ).all()
    }

    oneriler = [
        MekanOneriResponse(
            id=mekan.id,
            isim=mekan.isim,
            adres=mekan.adres,
            mutfak_turu=mekan.mutfak_turu,
            oneren=OneriKullanici(
                id=mekan.kullanici.id,
                isim=mekan.kullanici.isim,
                soyisim=mekan.kullanici.soyisim,
            ),
            oy_sayisi=oy_sayisi,
            oy_kullandim=mekan.id in benim_oylarim,
            created_at=mekan.created_at,
        )
        for mekan, oy_sayisi in rows
    ]

    return MekanOnerileriListesi(oneriler=oneriler, toplam=len(oneriler))


@router.post(
    "/oy/{mekan_id}",
    response_model=OyResponse,
    responses={400: {"model": ErrorResponse}, 401: _401, 404: {"model": ErrorResponse}},
    summary="Mekana oy ver veya geri al",
)
def oy_ver(
    mekan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    aktif_session = get_aktif_session(db)
    if not aktif_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Oylama sona erdi",
        )

    mekan = db.get(MekanOnerisi, mekan_id)
    if not mekan or mekan.session_id != aktif_session.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mekan bulunamadı",
        )

    mevcut_oy = db.execute(
        select(Oy).where(
            Oy.kullanici_id == current_user.id,
            Oy.mekan_id == mekan_id,
            Oy.session_id == aktif_session.id,
        )
    ).scalar_one_or_none()

    if mevcut_oy:
        db.delete(mevcut_oy)
        db.commit()
        oy_kullandim = False
    else:
        try:
            db.add(Oy(
                kullanici_id=current_user.id,
                mekan_id=mekan_id,
                session_id=aktif_session.id,
            ))
            db.commit()
            oy_kullandim = True
        except IntegrityError:
            db.rollback()
            oy_kullandim = True

    oy_sayisi = db.scalar(
        select(func.count(Oy.id)).where(
            Oy.mekan_id == mekan_id,
            Oy.session_id == aktif_session.id,
        )
    )
    return OyResponse(mekan_id=mekan_id, oy_sayisi=oy_sayisi, oy_kullandim=oy_kullandim)


@router.get(
    "/sonuclar",
    response_model=SonuclarResponse,
    responses={400: {"model": ErrorResponse}, 401: _401},
    summary="Bugünkü oy sonuçlarını listele",
)
def get_sonuclar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    aktif_session = _get_aktif_session_or_400(db)

    oy_sayisi_subq = (
        select(Oy.mekan_id, func.count(Oy.id).label("sayi"))
        .where(Oy.session_id == aktif_session.id)
        .group_by(Oy.mekan_id)
        .subquery()
    )

    mekan_rows = (
        db.query(
            MekanOnerisi,
            func.coalesce(oy_sayisi_subq.c.sayi, 0).label("oy_sayisi"),
        )
        .filter(MekanOnerisi.session_id == aktif_session.id)
        .outerjoin(oy_sayisi_subq, MekanOnerisi.id == oy_sayisi_subq.c.mekan_id)
        .order_by(oy_sayisi_subq.c.sayi.desc().nullslast())
        .all()
    )

    benim_oylarim = {
        row.mekan_id
        for row in db.execute(
            select(Oy.mekan_id).where(
                Oy.kullanici_id == current_user.id,
                Oy.session_id == aktif_session.id,
            )
        ).all()
    }

    sirali_mekanlar = [
        SonucMekan(
            sira=idx + 1,
            mekan_id=mekan.id,
            isim=mekan.isim,
            adres=mekan.adres,
            mutfak_turu=mekan.mutfak_turu,
            oneren=OneriKullanici(
                id=mekan.kullanici.id,
                isim=mekan.kullanici.isim,
                soyisim=mekan.kullanici.soyisim,
            ),
            oy_sayisi=oy_sayisi,
            oy_kullandim=mekan.id in benim_oylarim,
        )
        for idx, (mekan, oy_sayisi) in enumerate(mekan_rows)
    ]

    oy_kullananlar_rows = db.execute(
        select(Oy.kullanici_id, func.min(Oy.created_at).label("oy_zamani"))
        .where(Oy.session_id == aktif_session.id)
        .group_by(Oy.kullanici_id)
    ).all()

    oy_kullanan_ids = {row.kullanici_id for row in oy_kullananlar_rows}
    oy_zamani_map = {row.kullanici_id: row.oy_zamani for row in oy_kullananlar_rows}

    oy_kullanan_users = (
        db.execute(select(User).where(User.id.in_(oy_kullanan_ids))).scalars().all()
        if oy_kullanan_ids else []
    )

    oy_kullananlar = [
        OyKullananKullanici(
            id=u.id,
            isim=u.isim,
            soyisim=u.soyisim,
            oy_zamani=oy_zamani_map[u.id],
        )
        for u in oy_kullanan_users
    ]

    tum_kullanicilar = db.execute(select(User)).scalars().all()
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


@router.get(
    "/session/durum",
    response_model=SessionDurumResponse,
    responses={401: _401},
    summary="Bugünkü session durumunu getir",
)
def get_session_durum(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_aktif_session(db)
    if session:
        return SessionDurumResponse(
            aktif=True,
            tarih=session.tarih,
            durum=session.durum.value,
            mesaj="Oturum açık, öneri ve oy verebilirsiniz",
        )

    from datetime import date
    bugun = db.execute(
        select(LunchSession).where(LunchSession.tarih == date.today())
    ).scalar_one_or_none()

    if bugun:
        return SessionDurumResponse(
            aktif=False,
            tarih=bugun.tarih,
            durum=bugun.durum.value,
            mesaj="Bugünkü oturum kapandı, sonuçları görebilirsiniz",
        )

    return SessionDurumResponse(
        aktif=False,
        tarih=None,
        durum=None,
        mesaj="Bugün henüz oturum açılmadı, saat 09:00'da başlayacak",
    )


@router.get(
    "/gecmis",
    response_model=GecmisResponse,
    responses={401: _401},
    summary="Geçmiş session sonuçlarını listele",
)
def get_gecmis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = db.execute(
        select(LunchSession)
        .where(LunchSession.durum == SessionDurum.kapandi)
        .order_by(desc(LunchSession.tarih))
        .limit(30)
    ).scalars().all()

    gecmis = []
    for s in sessions:
        toplam_oneri = db.scalar(
            select(func.count(MekanOnerisi.id)).where(MekanOnerisi.session_id == s.id)
        )
        toplam_oy = db.scalar(
            select(func.count(Oy.id)).where(Oy.session_id == s.id)
        )
        kazanan_isim = None
        kazanan_mutfak = None
        if s.kazanan_mekan_id:
            kazanan = db.get(MekanOnerisi, s.kazanan_mekan_id)
            if kazanan:
                kazanan_isim = kazanan.isim
                kazanan_mutfak = kazanan.mutfak_turu

        gecmis.append(GecmisSonuc(
            session_id=s.id,
            tarih=s.tarih,
            kazanan_isim=kazanan_isim,
            kazanan_mutfak_turu=kazanan_mutfak,
            toplam_oneri=toplam_oneri or 0,
            toplam_oy=toplam_oy or 0,
        ))

    return GecmisResponse(gecmis=gecmis, toplam=len(gecmis))
