from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class Mekan(BaseModel):
    isim: str
    adres: str
    mutfak_turu: str
    puan: float
    aciklama: str
    mesafe_metre: int


class MekanListesiResponse(BaseModel):
    mekanlar: list[Mekan]
    konum: dict[str, float]
    toplam: int


class MekanOneriCreate(BaseModel):
    isim: str
    adres: str
    mutfak_turu: str


class OneriKullanici(BaseModel):
    id: int
    isim: str
    soyisim: str

    model_config = {"from_attributes": True}


class MekanOneriResponse(BaseModel):
    id: int
    isim: str
    adres: str
    mutfak_turu: str
    oneren: OneriKullanici
    oy_sayisi: int = 0
    oy_kullandim: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class MekanOnerileriListesi(BaseModel):
    oneriler: list[MekanOneriResponse]
    toplam: int


class OyResponse(BaseModel):
    mekan_id: int
    oy_sayisi: int
    oy_kullandim: bool


class SonucMekan(BaseModel):
    sira: int
    mekan_id: int
    isim: str
    adres: str
    mutfak_turu: str
    oneren: OneriKullanici
    oy_sayisi: int
    oy_kullandim: bool


class OyKullananKullanici(BaseModel):
    id: int
    isim: str
    soyisim: str
    oy_zamani: datetime


class SonuclarResponse(BaseModel):
    sirali_mekanlar: list[SonucMekan]
    oy_kullananlar: list[OyKullananKullanici]
    oy_kullanmayanlar: list[OneriKullanici]
    toplam_katilimci: int


class SessionDurumResponse(BaseModel):
    aktif: bool
    tarih: Optional[date]
    durum: Optional[str]
    acilis_saati: str = "09:00"
    kapanis_saati: str = "12:00"
    mesaj: str


class GecmisSonuc(BaseModel):
    session_id: int
    tarih: date
    kazanan_isim: Optional[str]
    kazanan_mutfak_turu: Optional[str]
    toplam_oneri: int
    toplam_oy: int


class GecmisResponse(BaseModel):
    gecmis: list[GecmisSonuc]
    toplam: int
