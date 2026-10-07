from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, Team, Tournament
from app.services.pdf_identity_service import PDFIdentityService, normalize_identity_name


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _fields():
    return {
        "tournament": {"value": "Metropolitano Apertura Zona A", "confidence": "high", "source": {"label": "Torneo"}},
        "category": {"value": "Mayores", "confidence": "high", "source": {"label": "Categoria"}},
        "date": {"value": "2026-05-31", "confidence": "high", "source": {"label": "Fecha"}},
        "home_name": {"value": "C.A. Banfield B", "confidence": "high", "source": {"label": "Equipo local"}},
        "away_name": {"value": "S.A.P.A.", "confidence": "high", "source": {"label": "Equipo visitante"}},
    }


def test_normalized_banfield_and_sapa_identities_are_reused_with_evidence():
    session, engine = _session()
    banfield, sapa = Team(name="CA Banfield B"), Team(name="SAPA")
    tournament = Tournament(name="Metropolitano Apertura Zona A", category="Mayores", year=2026)
    session.add_all([banfield, sapa, tournament])
    session.flush()
    session.add_all([
        Player(name="Ana Gómez", team_id=banfield.id, default_jersey_number=7),
        Player(name="Bea Perez", team_id=sapa.id, default_jersey_number=8),
    ])
    session.commit()

    proposals = PDFIdentityService.propose(session, _fields(), {"players": [{"name": "Ana Gomez", "number": 7}]}, {"players": [{"name": "Bea Pérez", "number": 8}]})

    assert normalize_identity_name(" S.A.P.A. ") == "sapa"
    assert proposals["tournament"]["candidate"]["id"] == tournament.id
    assert proposals["home_team"]["candidate"]["id"] == banfield.id
    assert proposals["away_team"]["candidate"]["id"] == sapa.id
    assert proposals["home_players"][0]["candidate"]["name"] == "Ana Gómez"
    assert proposals["home_team"]["evidence"]["source"]["label"] == "Equipo local"
    assert "roster matches player IDs" in proposals["home_team"]["rationale"][1]
    engine.dispose()


def test_ambiguous_duplicates_are_never_auto_merged_and_keep_options():
    session, engine = _session()
    team = Team(name="SAPA")
    session.add(team)
    session.flush()
    session.add_all([
        Tournament(name="Metropolitano Apertura Zona A", category="Mayores", year=2025),
        Tournament(name="Metropolitano Apertura Zona A", category="Mayores", year=2026),
        Player(name="Ana Gomez", team_id=team.id, default_jersey_number=7),
        Player(name="Ana Gómez", team_id=team.id, default_jersey_number=7),
    ])
    session.commit()
    fields = _fields()
    fields["home_name"] = {"value": "SAPA", "confidence": "high", "source": {"label": "Equipo local"}}

    proposals = PDFIdentityService.propose(session, fields, {"players": [{"name": "Ana Gómez", "number": 7}]}, {"players": []})

    assert proposals["tournament"]["candidate"] is None
    assert len(proposals["tournament"]["options"]) == 2
    assert proposals["home_team"]["candidate"]["id"] == team.id
    assert proposals["home_players"][0]["candidate"] is None
    assert len(proposals["home_players"][0]["options"]) == 2
    assert proposals["home_players"][0]["warnings"] == ["Multiple normalized player candidates were found"]
    assert session.query(Player).count() == 2
    assert session.query(Tournament).count() == 2
    engine.dispose()
