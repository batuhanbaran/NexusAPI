# NexusAPI

GibMobil Hackathon projesi için geliştirilmiş FastAPI tabanlı backend. JWT kimlik doğrulama ve LunchSwipe servisi içerir.

## Teknoloji

- **Python 3.9+**
- **FastAPI** — web framework
- **SQLAlchemy 2.0** — ORM
- **PostgreSQL** (prod) / **SQLite** (local)
- **bcrypt** — şifre hashleme
- **python-jose** — JWT token
- **Groq AI** (llama-3.3-70b-versatile) — mekan önerisi

## Kurulum

```bash
git clone <repo-url>
cd NexusAPI

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

`.env.example` dosyasını kopyalayıp düzenle:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql://user:password@localhost:5432/nexusapi
SECRET_KEY=super-gizli-anahtar
ACCESS_TOKEN_EXPIRE_MINUTES=60
GROQ_API_KEY=gsk_...
LUNCH_LATITUDE=39.9564292
LUNCH_LONGITUDE=32.8526627
```

## Çalıştırma

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Referansı

### Auth

| Method | Endpoint | Auth | Açıklama |
|--------|----------|------|----------|
| `POST` | `/api/auth/register` | — | Yeni kullanıcı kaydı |
| `POST` | `/api/auth/login` | — | Giriş → JWT token döner |
| `GET` | `/api/auth/me` | Bearer | Giriş yapan kullanıcı bilgisi |

#### Kayıt

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"isim":"Ahmet","soyisim":"Yılmaz","mail":"ahmet@example.com","cinsiyet":"erkek","sifre":"Test123!"}'
```

#### Giriş

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"mail":"ahmet@example.com","sifre":"Test123!"}'
```

Yanıt: `access_token` + kullanıcı bilgisi

---

### LunchSwipe

Tüm endpointler `Authorization: Bearer <token>` gerektirir.

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/api/lunch/mekanlar` | Groq AI ile konum bazlı mekan listesi |
| `POST` | `/api/lunch/oner` | Kullanıcı mekan önerisi ekle |
| `GET` | `/api/lunch/oneriler` | Kullanıcı önerilerini oy bilgisiyle listele |
| `POST` | `/api/lunch/oy/{mekan_id}` | Mekana oy ver / geri al (toggle) |
| `GET` | `/api/lunch/sonuclar` | Leaderboard + oy kullananlar / kullanmayanlar |

---

#### AI Mekan Listesi — `GET /api/lunch/mekanlar`

```bash
curl http://localhost:8000/api/lunch/mekanlar \
  -H "Authorization: Bearer <token>"
```

```json
{
  "mekanlar": [
    {
      "isim": "Hacı Arif Bey",
      "adres": "Kızılay, Ankara",
      "mutfak_turu": "Türk",
      "puan": 4.5,
      "aciklama": "Ankara'nın en iyi döner mekanlarından biri.",
      "mesafe_metre": 320
    }
  ],
  "konum": { "lat": 39.9564292, "lng": 32.8526627 },
  "toplam": 10
}
```

---

#### Mekan Öner — `POST /api/lunch/oner`

```bash
curl -X POST http://localhost:8000/api/lunch/oner \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"isim":"Hacı Arif Bey","adres":"Kızılay, Ankara","mutfak_turu":"Türk"}'
```

---

#### Kullanıcı Önerileri — `GET /api/lunch/oneriler`

Her mekan için oy sayısı ve giriş yapan kullanıcının oy durumu döner.

```bash
curl http://localhost:8000/api/lunch/oneriler \
  -H "Authorization: Bearer <token>"
```

```json
{
  "oneriler": [
    {
      "id": 1,
      "isim": "Hacı Arif Bey",
      "adres": "Kızılay, Ankara",
      "mutfak_turu": "Türk",
      "oneren": { "id": 1, "isim": "Ahmet", "soyisim": "Yılmaz" },
      "oy_sayisi": 5,
      "oy_kullandim": true,
      "created_at": "2026-06-10T11:15:49Z"
    }
  ],
  "toplam": 1
}
```

---

#### Oy Ver / Geri Al — `POST /api/lunch/oy/{mekan_id}`

Aynı mekana iki kez istek: oy geri alınır (toggle).

```bash
curl -X POST http://localhost:8000/api/lunch/oy/1 \
  -H "Authorization: Bearer <token>"
```

```json
{ "mekan_id": 1, "oy_sayisi": 6, "oy_kullandim": true }
```

---

#### Sonuçlar — `GET /api/lunch/sonuclar`

En çok oylanan mekanlar sıralı gelir. Oy kullananlar ve kullanmayanlar ayrı listelerde döner.

```bash
curl http://localhost:8000/api/lunch/sonuclar \
  -H "Authorization: Bearer <token>"
```

```json
{
  "sirali_mekanlar": [
    {
      "sira": 1,
      "mekan_id": 1,
      "isim": "Hacı Arif Bey",
      "mutfak_turu": "Türk",
      "oneren": { "id": 1, "isim": "Ahmet", "soyisim": "Yılmaz" },
      "oy_sayisi": 42,
      "oy_kullandim": true
    }
  ],
  "oy_kullananlar": [
    { "id": 1, "isim": "Ahmet", "soyisim": "Yılmaz", "oy_zamani": "2026-06-10T10:42:00Z" },
    { "id": 3, "isim": "Mehmet", "soyisim": "Kaya", "oy_zamani": "2026-06-10T10:12:00Z" }
  ],
  "oy_kullanmayanlar": [
    { "id": 2, "isim": "Ayşe", "soyisim": "Demir" }
  ],
  "toplam_katilimci": 2
}
```

---

### Diğer

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/health` | Servis sağlık kontrolü |
| `GET` | `/` | Login sayfası |
| `GET` | `/kayit` | Kayıt sayfası |

---

## Proje Yapısı

```
app/
├── main.py          # FastAPI uygulama girişi
├── config.py        # Ortam değişkenleri (pydantic-settings)
├── database.py      # SQLAlchemy engine & session
├── models/
│   ├── user.py          # Kullanıcı modeli
│   ├── mekan_onerisi.py # Mekan önerisi modeli
│   └── oy.py            # Oy modeli (unique: kullanıcı + mekan)
├── routers/
│   ├── auth.py      # Kimlik doğrulama endpoint'leri
│   └── lunch.py     # LunchSwipe endpoint'leri
├── schemas/
│   ├── user.py      # Auth Pydantic şemaları
│   └── lunch.py     # LunchSwipe Pydantic şemaları
├── services/
│   ├── auth.py      # JWT, bcrypt yardımcıları
│   └── lunch.py     # Groq AI entegrasyonu
└── static/          # Login/register HTML sayfaları
```

## Deploy (Render)

`render.yaml` ile Render.com'a deploy edilir. Gerekli environment variable'lar:

- `DATABASE_URL`
- `SECRET_KEY`
- `GROQ_API_KEY`
- `LUNCH_LATITUDE`
- `LUNCH_LONGITUDE`
