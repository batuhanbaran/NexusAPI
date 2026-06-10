from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MekanOnerisi(Base):
    __tablename__ = "mekan_onerileri"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    isim: Mapped[str] = mapped_column(String(200), nullable=False)
    adres: Mapped[str] = mapped_column(String(500), nullable=False)
    mutfak_turu: Mapped[str] = mapped_column(String(100), nullable=False)
    onerilen_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    kullanici: Mapped["User"] = relationship("User", lazy="joined")  # noqa: F821
