import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, lunch

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations are run via: alembic upgrade head
    yield


app = FastAPI(title="NexusAPI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Beklenmeyen hata: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası, lütfen tekrar deneyin"},
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
