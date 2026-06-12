from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionDurum(str, enum.Enum):
    aktif = "aktif"
    kapandi = "kapandi"


class LunchSession(Base):
    __tablename__ = "lunch_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tarih: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    durum: Mapped[SessionDurum] = mapped_column(
        Enum(SessionDurum), nullable=False, default=SessionDurum.aktif
    )
    kazanan_mekan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("mekan_onerileri.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kazanan: Mapped[Optional[MekanOnerisi]] = relationship(  # noqa: F821
        "MekanOnerisi", foreign_keys=[kazanan_mekan_id], lazy="joined"
    )
