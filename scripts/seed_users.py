"""Örnek kullanıcıları veritabanına ekler."""

from app.database import Base, SessionLocal, engine
from app.models.user import Cinsiyet, User
from app.services.auth import get_user_by_mail, hash_password

SAMPLE_USERS = [
    {
        "isim": "Ahmet",
        "soyisim": "Yılmaz",
        "mail": "ahmet@example.com",
        "cinsiyet": Cinsiyet.erkek,
        "sifre": "Test123!",
    },
    {
        "isim": "Ayşe",
        "soyisim": "Demir",
        "mail": "ayse@example.com",
        "cinsiyet": Cinsiyet.kadin,
        "sifre": "Test123!",
    },
    {
        "isim": "Can",
        "soyisim": "Öztürk",
        "mail": "can@example.com",
        "cinsiyet": Cinsiyet.diger,
        "sifre": "Test123!",
    },
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for data in SAMPLE_USERS:
            if get_user_by_mail(db, data["mail"]):
                print(f"Zaten var: {data['mail']}")
                continue

            user = User(
                isim=data["isim"],
                soyisim=data["soyisim"],
                mail=data["mail"],
                cinsiyet=data["cinsiyet"],
                sifre_hash=hash_password(data["sifre"]),
            )
            db.add(user)
            print(f"Eklendi: {data['isim']} {data['soyisim']} ({data['mail']})")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
