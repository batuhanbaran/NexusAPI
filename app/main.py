from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="NexusAPI", version="1.0.0", lifespan=lifespan)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(auth.router)


@app.get("/")
def login_page():
    return FileResponse(static_dir / "login.html")


@app.get("/kayit")
def register_page():
    return FileResponse(static_dir / "register.html")


@app.get("/health")
def health():
    return {"status": "ok"}
