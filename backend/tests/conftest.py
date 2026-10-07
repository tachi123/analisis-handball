from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Club,
    CompetitionTeam,
    Player,
    Round,
    ScheduledMatch,
    Season,
    StageRoster,
    TeamRegistration,
    TournamentStage,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_config(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config, database_url


# ─── Shared Competition Layer Fixtures ───


@pytest.fixture
def session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def season(session):
    """Create a test season."""
    s = Season(year=2026, description="Test Season")
    session.add(s)
    session.flush()
    return s


@pytest.fixture
def stage(session, season):
    """Create a test tournament stage."""
    st = TournamentStage(
        season_id=season.id,
        name="Clausura Permanencia",
        category="Mayores",
        division="3ª División",
        gender="Masculino",
    )
    session.add(st)
    session.flush()
    return st


@pytest.fixture
def club(session):
    """Create a test club."""
    c = Club(name="Banfield", short_name="BAN")
    session.add(c)
    session.flush()
    return c


@pytest.fixture
def competition_team(session, club, stage):
    """Create a test competition team with suffix B."""
    ct = CompetitionTeam(club_id=club.id, stage_id=stage.id, suffix="B")
    session.add(ct)
    session.flush()
    return ct


@pytest.fixture
def registration(session, competition_team, stage):
    """Create a test team registration."""
    reg = TeamRegistration(competition_team_id=competition_team.id, stage_id=stage.id)
    session.add(reg)
    session.flush()
    return reg


@pytest.fixture
def round_(session, stage):
    """Create a test round."""
    r = Round(stage_id=stage.id, round_number=1)
    session.add(r)
    session.flush()
    return r


@pytest.fixture
def player(session):
    """Create a test player."""
    p = Player(name="Juan Perez", default_jersey_number=10)
    session.add(p)
    session.flush()
    return p


@pytest.fixture
def alembic_engine(alembic_config):
    """Create engine from alembic config for migration tests."""
    config, database_url = alembic_config
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def migrated_db(alembic_config):
    """Apply all migrations and return engine."""
    config, database_url = alembic_config
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        command.downgrade(config, "base")
        engine.dispose()
