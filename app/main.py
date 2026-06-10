import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.models import mekan_onerisi  # noqa: F401 — tablo create_all'da görünsün
from app.models import oy  # noqa: F401
from app.routers import auth
from app.routers import lunch

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="NexusAPI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nexus-frontend-coqa.onrender.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Beklenmeyen hata: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"hata": "Sunucu hatası, lütfen tekrar deneyin", "kod": 500},
    )


static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(auth.router)
app.include_router(lunch.router)


@app.get("/")
def login_page():
    return FileResponse(static_dir / "login.html")


@app.get("/kayit")
def register_page():
    return FileResponse(static_dir / "register.html")


@app.get("/health")
def health():
    return {"status": "ok"}
