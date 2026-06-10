import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Cinsiyet(str, enum.Enum):
    erkek = "erkek"
    kadin = "kadin"
    diger = "diger"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    isim: Mapped[str] = mapped_column(String(100), nullable=False)
    soyisim: Mapped[str] = mapped_column(String(100), nullable=False)
    mail: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    cinsiyet: Mapped[Cinsiyet] = mapped_column(Enum(Cinsiyet), nullable=False)
    sifre_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
