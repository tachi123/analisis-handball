from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .database import engine, Base, SessionLocal
from .api.routes import tournaments, teams, players, matches, events, clips, pdf, auth

# Import all models so SQLAlchemy knows about them before create_all
from . import models  # noqa: F401

logger = logging.getLogger(__name__)


def _seed_superadmin():
    """Create the initial superadmin user if it doesn't exist yet."""
    email = os.getenv("SUPERADMIN_EMAIL", "admin@sapa.com")
    password = os.getenv("SUPERADMIN_PASSWORD", "changeme123")
    from .services.auth_service import AuthService
    db = SessionLocal()
    try:
        existing = AuthService.get_by_email(db, email)
        if not existing:
            AuthService.create_user(db, email, password, "Super Admin", "superadmin")
            logger.info("Superadmin creado: %s", email)
        else:
            logger.info("Superadmin ya existe: %s", email)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_superadmin()
    yield


app = FastAPI(
    title="SAPA Stats API",
    version="2.0.0",
    description="API para análisis de partidos de handball",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(tournaments.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(players.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(clips.router, prefix="/api/v1")
app.include_router(pdf.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
