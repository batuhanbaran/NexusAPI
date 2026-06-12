from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.session import session_baslat, session_kapat

logger = logging.getLogger(__name__)

# Türkiye saati (UTC+3)
_TZ = "Europe/Istanbul"

scheduler = AsyncIOScheduler(timezone=_TZ)


def _job_session_baslat() -> None:
    """Her gün 09:00 TR saatinde çalışır — yeni lunch session açar."""
    logger.info("Scheduler: session başlatılıyor...")
    db = SessionLocal()
    try:
        session = session_baslat(db)
        logger.info("Scheduler: session açıldı id=%s", session.id)
    except Exception as exc:
        logger.exception("Scheduler: session başlatılamadı: %s", exc)
    finally:
        db.close()


def _job_session_kapat() -> None:
    """Her gün 12:00 TR saatinde çalışır — aktif session'ı kapatır."""
    logger.info("Scheduler: session kapatılıyor...")
    db = SessionLocal()
    try:
        session = session_kapat(db)
        if session:
            logger.info("Scheduler: session kapatıldı id=%s kazanan=%s", session.id, session.kazanan_mekan_id)
        else:
            logger.warning("Scheduler: kapatılacak aktif session yok.")
    except Exception as exc:
        logger.exception("Scheduler: session kapatılamadı: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        _job_session_baslat,
        CronTrigger(hour=9, minute=0, timezone=_TZ),
        id="session_baslat",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_session_kapat,
        CronTrigger(hour=12, minute=0, timezone=_TZ),
        id="session_kapat",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler başlatıldı — session 09:00 açılır, 12:00 kapanır (TR saati)")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler durduruldu.")
