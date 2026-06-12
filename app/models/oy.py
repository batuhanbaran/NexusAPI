from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Oy(Base):
    __tablename__ = "oylar"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("lunch_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kullanici_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    mekan_id: Mapped[int] = mapped_column(
        ForeignKey("mekan_onerileri.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kullanici: Mapped["User"] = relationship("User", lazy="joined")  # noqa: F821
    mekan: Mapped["MekanOnerisi"] = relationship("MekanOnerisi", lazy="joined")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("kullanici_id", "mekan_id", name="uq_kullanici_mekan_oyu"),
    )
