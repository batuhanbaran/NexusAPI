from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import Cinsiyet


class UserCreate(BaseModel):
    isim: str = Field(..., min_length=1, max_length=100)
    soyisim: str = Field(..., min_length=1, max_length=100)
    mail: EmailStr
    cinsiyet: Cinsiyet
    sifre: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    mail: EmailStr
    sifre: str


class UserResponse(BaseModel):
    id: int
    isim: str
    soyisim: str
    mail: EmailStr
    cinsiyet: Cinsiyet
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
