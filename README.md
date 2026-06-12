# NexusAPI

GibMobil Hackathon projesi için geliştirilmiş FastAPI tabanlı backend. JWT kimlik doğrulama ve LunchSwipe servisi içerir.

## Teknoloji

- **Python 3.9+**
- **FastAPI** — web framework
- **SQLAlchemy 2.0** — ORM
- **Alembic** — veritabanı migration
- **APScheduler** — otomatik session zamanlayıcısı
- **PostgreSQL** (prod) / **SQLite** (local)
- **bcrypt** — şifre hashleme
- **python-jose** — JWT token
- **Groq AI** (llama-3.3-70b-versatile) — mekan önerisi

## Kurulum

```bash
git clone https://github.com/batuhanbaran/NexusAPI.git
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
CORS_ORIGINS=http://localhost:5173
GROQ_API_KEY=gsk_...
LUNCH_LATITUDE=39.9564292
LUNCH_LONGITUDE=32.8526627
```

## Çalıştırma

```bash
# Migration'ları uygula
alembic upgrade head

# Sunucuyu başlat
uvicorn app.main:app --reload --port 8000
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Proje Yapısı

```
app/
├── main.py           # FastAPI uygulama girişi, CORS, lifespan
├── config.py         # Ortam değişkenleri (pydantic-settings)
├── database.py       # SQLAlchemy engine & session
├── dependencies.py   # Ortak FastAPI dependency'ler (get_current_user)
├── cache.py          # In-memory TTL cache
├── scheduler.py      # APScheduler — session açma/kapama job'ları
├── models/
│   ├── user.py           # Kullanıcı modeli
│   ├── lunch_session.py  # Günlük oturum modeli
│   ├── mekan_onerisi.py  # Mekan önerisi modeli
│   └── oy.py             # Oy modeli (unique: kullanıcı + mekan)
├── routers/
│   ├── auth.py       # Kimlik doğrulama endpoint'leri
│   └── lunch.py      # LunchSwipe endpoint'leri
├── schemas/
│   ├── user.py       # Auth Pydantic şemaları
│   └── lunch.py      # LunchSwipe Pydantic şemaları
├── services/
│   ├── auth.py       # JWT, bcrypt yardımcıları
│   ├── lunch.py      # Groq AI entegrasyonu (AsyncGroq)
│   └── session.py    # Session açma/kapama/kazanan logic
└── static/           # Login/register HTML sayfaları
alembic/              # Veritabanı migration dosyaları
```

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

> **Session Sistemi:** Her gün **09:00'da** yeni bir oturum otomatik açılır, **12:00'da** kapanır (Türkiye saati).
> Session dışında öneri ve oy kabul edilmez.

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/api/lunch/mekanlar` | Groq AI ile konum bazlı mekan listesi (5 dk cache) |
| `POST` | `/api/lunch/oner` | Bugünkü session'a mekan öner |
| `GET` | `/api/lunch/oneriler` | Bugünkü önerileri oy bilgisiyle listele |
| `POST` | `/api/lunch/oy/{mekan_id}` | Mekana oy ver / geri al (toggle) |
| `GET` | `/api/lunch/sonuclar` | Bugünkü leaderboard + oy kullananlar / kullanmayanlar |

#### AI Mekan Listesi — `GET /api/lunch/mekanlar`

Backendde tanımlı GPS koordinatına göre Groq AI üzerinden öğle yemeği mekanları döner.
Sonuç **5 dakika boyunca cache'lenir** — aynı koordinat için Groq'a gereksiz istek gitmez.

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

#### Mekan Öner — `POST /api/lunch/oner`

```bash
curl -X POST http://localhost:8000/api/lunch/oner \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"isim":"Hacı Arif Bey","adres":"Kızılay, Ankara","mutfak_turu":"Türk"}'
```

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
      "created_at": "2026-06-11T09:00:00Z"
    }
  ],
  "toplam": 1
}
```

#### Oy Ver / Geri Al — `POST /api/lunch/oy/{mekan_id}`

Aynı mekana iki kez istek atılırsa oy geri alınır (toggle).

```bash
curl -X POST http://localhost:8000/api/lunch/oy/1 \
  -H "Authorization: Bearer <token>"
```

```json
{ "mekan_id": 1, "oy_sayisi": 6, "oy_kullandim": true }
```

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
    { "id": 1, "isim": "Ahmet", "soyisim": "Yılmaz", "oy_zamani": "2026-06-11T09:42:00Z" }
  ],
  "oy_kullanmayanlar": [
    { "id": 2, "isim": "Ayşe", "soyisim": "Demir" }
  ],
  "toplam_katilimci": 1
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

## Deploy (Render)

`render.yaml` ile Render.com'a otomatik deploy edilir. `startCommand` migration'ları otomatik uygular:

```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Gerekli environment variable'lar:

| Değişken | Açıklama |
|----------|----------|
| `DATABASE_URL` | PostgreSQL bağlantı URL'i |
| `SECRET_KEY` | JWT imzalama anahtarı |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token geçerlilik süresi (dk) |
| `CORS_ORIGINS` | İzin verilen origin'ler (virgülle ayrılmış) |
| `GROQ_API_KEY` | Groq API anahtarı |
| `LUNCH_LATITUDE` | Öğle yemeği koordinatı — enlem |
| `LUNCH_LONGITUDE` | Öğle yemeği koordinatı — boylam |
