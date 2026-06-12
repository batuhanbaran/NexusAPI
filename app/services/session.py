from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.lunch_session import LunchSession, SessionDurum
from app.models.mekan_onerisi import MekanOnerisi
from app.models.oy import Oy

logger = logging.getLogger(__name__)


def get_aktif_session(db: Session) -> Optional[LunchSession]:
    """Bugünün aktif session'ını döner. Yoksa None."""
    return db.execute(
        select(LunchSession).where(
            LunchSession.tarih == date.today(),
            LunchSession.durum == SessionDurum.aktif,
        )
    ).scalar_one_or_none()


def session_baslat(db: Session) -> LunchSession:
    """Bugün için yeni session açar. Zaten varsa mevcut session'ı döner."""
    mevcut = db.execute(
        select(LunchSession).where(LunchSession.tarih == date.today())
    ).scalar_one_or_none()

    if mevcut:
        logger.info("Bugün için session zaten mevcut: id=%s durum=%s", mevcut.id, mevcut.durum)
        return mevcut

    yeni = LunchSession(tarih=date.today(), durum=SessionDurum.aktif)
    db.add(yeni)
    db.commit()
    db.refresh(yeni)
    logger.info("Yeni lunch session açıldı: id=%s tarih=%s", yeni.id, yeni.tarih)
    return yeni


def session_kapat(db: Session) -> Optional[LunchSession]:
    """Bugünün aktif session'ını kapatır, kazananı belirler."""
    session = get_aktif_session(db)
    if not session:
        logger.warning("Kapatılacak aktif session bulunamadı.")
        return None

    # En çok oy alan mekanı bul
    kazanan_row = db.execute(
        select(Oy.mekan_id, func.count(Oy.id).label("oy_sayisi"))
        .where(Oy.session_id == session.id)
        .group_by(Oy.mekan_id)
        .order_by(func.count(Oy.id).desc())
        .limit(1)
    ).first()

    session.durum = SessionDurum.kapandi
    session.kazanan_mekan_id = kazanan_row.mekan_id if kazanan_row else None
    db.commit()
    db.refresh(session)

    logger.info(
        "Session kapatıldı: id=%s kazanan_mekan_id=%s",
        session.id, session.kazanan_mekan_id,
    )
    return session
