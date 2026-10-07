from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from .database import SessionLocal
from .api.routes import analysis, analysis_events, canonical_analysis, tournaments, teams, players, matches, events, clips, pdf, auth, reports, goalkeeper_shots, stage_performance
from .services.canonical_analysis_service import LegacyWriteBlockedError
from .services.sheets_service import validate_report_publisher_configuration

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
    validate_report_publisher_configuration()
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
app.include_router(analysis_events.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(clips.router, prefix="/api/v1")
app.include_router(pdf.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(goalkeeper_shots.router, prefix="/api/v1")
app.include_router(canonical_analysis.router, prefix="/api/v1")
app.include_router(stage_performance.router, prefix="/api/v1")


@app.exception_handler(LegacyWriteBlockedError)
def legacy_write_blocked_handler(_request: Request, error: LegacyWriteBlockedError):
    """Shared cutover boundary: legacy analytical writes answer 409 once canonical."""
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.get("/health")
def health():
    return {"status": "ok"}
