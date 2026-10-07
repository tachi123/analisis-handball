import pdfplumber
import os
import hashlib
import io
import uuid
import json
from datetime import date
from pathlib import Path, PureWindowsPath

from sqlalchemy.orm import Session, joinedload, object_session
from sqlalchemy.exc import IntegrityError

from ..models import CompetitionTeam, FixtureImportEntry, Match, MatchSquad, OfficialSnapshot, OfficialSnapshotPlayer, Player, ScheduledMatch, StageRoster, Team, TeamRegistration, TournamentStage
from ..schemas import MatchPDFConfirmation, PDFConfirmedPlayer, PDFConfirmedTeam, FixtureConfirmation, PDFImportConfirmation
from .pdf_header_parser import parse_header_pages


# The Compose backend mounts the immutable local evidence corpus at /app/resources.
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOURCES_DIR = Path(os.getenv("OFFICIAL_RESOURCES_DIR", "/app/resources"))
PLANILLAS_INDEXED_DIR = RESOURCES_DIR / "planillas" / "_indexed"


class PDFParseError(ValueError):
    pass


class OfficialSheetSourceUnavailable(ValueError):
    pass


class PDFService:
    PDF_DIR = "data/pdfs"
    MAX_SIZE_BYTES = 10 * 1024 * 1024
    MAX_PAGES = 10

    @staticmethod
    def official_sheet(db: Session, match_id: int) -> OfficialSnapshot | None:
        return db.query(OfficialSnapshot).options(joinedload(OfficialSnapshot.players)).filter(
            OfficialSnapshot.match_id == match_id,
            OfficialSnapshot.is_confirmed.is_(True),
        ).order_by(OfficialSnapshot.created_at.desc(), OfficialSnapshot.id.desc()).first()

    @staticmethod
    def official_sheet_read(snapshot: OfficialSnapshot) -> dict:
        def team(side: str, name: str, score: int) -> dict:
            players = [item for item in snapshot.players if item.side == side]
            return {
                "name": name,
                "score": score,
                "players": [{
                    "player_id": item.player_id, "name": item.name, "jersey_number": item.jersey_number,
                    "official_goals": item.official_goals, "official_yellow": item.official_yellow,
                    "official_2min": item.official_2min, "official_red": item.official_red,
                    "official_blue": item.official_blue,
                } for item in sorted(players, key=lambda item: (item.jersey_number, item.id))],
            }
        return {
            "snapshot_id": snapshot.id, "confirmed_date": snapshot.confirmed_date,
            "home": team("home", snapshot.home_team_name, snapshot.home_score),
            "away": team("away", snapshot.away_team_name, snapshot.away_score),
            "provenance": {
                "filename": snapshot.source_filename, "content_type": snapshot.source_content_type,
                "size_bytes": snapshot.source_size_bytes, "sha256": snapshot.source_sha256,
                "page_count": snapshot.source_page_count,
            },
            "pdf_available": PDFService.official_sheet_pdf_path(snapshot) is not None,
        }

    @staticmethod
    def official_sheet_pdf_path(snapshot: OfficialSnapshot) -> Path | None:
        roots = [Path(value).expanduser().resolve() for value in os.getenv("OFFICIAL_EVIDENCE_ROOTS", "").split(os.pathsep) if value]
        roots.append((PROJECT_ROOT / PDFService.PDF_DIR).resolve())
        source = Path(snapshot.source_path)
        candidates = [source.resolve() if source.is_absolute() else (PROJECT_ROOT / source).resolve()]
        # Imported snapshots may retain a Windows workstation path. Rebase only the
        # suffix below the approved planillas root; never expose or follow that path.
        normalized = str(snapshot.source_path).replace("\\", "/")
        marker = "/resources/planillas/"
        if marker in normalized:
            relative = normalized.split(marker, 1)[1]
            candidates.extend(root / relative for root in roots)
        else:
            filename = PureWindowsPath(snapshot.source_path).name
            candidates.extend(root / filename for root in roots)
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate.suffix.lower() != ".pdf" or not candidate.is_file():
                continue
            if any(candidate.is_relative_to(root) for root in roots):
                return candidate
        return None

    @staticmethod
    def save_pdf(file_bytes: bytes, filename: str, match_id_prefix: str = "match") -> str:
        os.makedirs(PDFService.PDF_DIR, exist_ok=True)
        safe_filename = os.path.basename(filename.replace("\\", "/"))
        file_path = os.path.join(PDFService.PDF_DIR, f"{match_id_prefix}_{safe_filename}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        return file_path

    @staticmethod
    def list_fixtures(db: Session) -> list[ScheduledMatch]:
        return db.query(ScheduledMatch).join(FixtureImportEntry).filter(
            FixtureImportEntry.kind == "match"
        ).options(
            joinedload(ScheduledMatch.stage).joinedload(TournamentStage.season),
            joinedload(ScheduledMatch.home_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
            joinedload(ScheduledMatch.away_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
            joinedload(ScheduledMatch.analysis_match),
            joinedload(ScheduledMatch.analysis_match).joinedload(Match.official_snapshots),
        ).order_by(ScheduledMatch.scheduled_date, ScheduledMatch.id).all()

    @staticmethod
    def fixture_read(fixture: ScheduledMatch) -> dict:
        db = object_session(fixture)
        if db is None:
            raise ValueError("fixture must be attached to a database session")
        def registration(value):
            team = value.competition_team
            return {"id": value.id, "display_name": team.display_name, "variant": team.variant}
        snapshot = next((item for item in (fixture.analysis_match.official_snapshots if fixture.analysis_match else []) if item.is_confirmed), None)
        roster_ready = snapshot is not None and PDFService._roster_is_ready(db, fixture, snapshot)
        unresolved = [player for player in (snapshot.players if snapshot else []) if player.player_id is None]
        return {
            "fixture_key": fixture.fixture_key,
            "stage": {
                "id": fixture.stage.id,
                "season_year": fixture.stage.season.year,
                "name": fixture.stage.name,
                "category": fixture.stage.category,
                "division": fixture.stage.division,
                "gender": fixture.stage.gender,
            },
            "home_registration": registration(fixture.home_registration),
            "away_registration": registration(fixture.away_registration),
            "scheduled_date": fixture.scheduled_date,
            "venue": fixture.venue, "court": fixture.court, "match_time": fixture.match_time,
            "source_home_score": fixture.source_home_score,
            "source_away_score": fixture.source_away_score,
            "result_status": fixture.result_status,
            "linked_match_id": fixture.analysis_match.id if fixture.analysis_match else None,
            "official_snapshot_id": snapshot.id if snapshot else None,
            "is_preloaded": snapshot is not None,
            "youtube_link": fixture.analysis_match.youtube_link or "" if fixture.analysis_match else "",
            "roster_status": "not_confirmed" if snapshot is None else "ready" if roster_ready else "needs_identity_resolution",
            "unresolved_roster_players": len(unresolved),
        }

    @staticmethod
    def preloaded_fixture(db: Session, fixture_key: str) -> ScheduledMatch:
        fixtures = PDFService.list_fixtures(db)
        selected = next(
            (
                item for item in fixtures
                if item.fixture_key == fixture_key and PDFService._confirmed_snapshot(item) is not None
            ),
            None,
        )
        if selected is None:
            raise ValueError("El fixture no tiene evidencia oficial confirmada")
        return selected

    @staticmethod
    def fixture_roster(db: Session, fixture_key: str) -> dict:
        fixture = PDFService.preloaded_fixture(db, fixture_key)
        snapshot = PDFService._confirmed_snapshot(fixture)
        if snapshot is None:
            raise ValueError("El fixture no tiene evidencia oficial confirmada")
        teams = {"home": fixture.analysis_match.home_team_id, "away": fixture.analysis_match.away_team_id}
        return {
            "fixture": PDFService.fixture_read(fixture),
            "players": [{
                "id": item.id, "side": item.side, "name": item.name, "jersey_number": item.jersey_number,
                "player_id": item.player_id,
                "candidates": PDFService._identity_candidates(db, teams[item.side], item.name),
            } for item in sorted(snapshot.players, key=lambda item: (item.side, item.jersey_number, item.id))],
        }

    @staticmethod
    def resolve_fixture_roster(db: Session, fixture_key: str, resolutions) -> dict:
        fixture = PDFService.preloaded_fixture(db, fixture_key)
        match = fixture.analysis_match
        snapshot = PDFService._confirmed_snapshot(fixture)
        if snapshot is None:
            raise ValueError("El fixture no tiene evidencia oficial confirmada")
        snapshot_players = {item.id: item for item in snapshot.players}
        requested = {item.snapshot_player_id: item for item in resolutions}
        unresolved = {item.id for item in snapshot.players if item.player_id is None}
        if len(requested) != len(resolutions):
            raise ValueError("each unresolved official roster row must have exactly one resolution")
        if set(requested) != unresolved:
            raise ValueError("all unresolved official roster rows must be resolved together")
        selected_player_ids = [
            resolution.existing_player_id
            for resolution in requested.values()
            if resolution.existing_player_id is not None
        ]
        assigned_player_ids = [
            row.player_id for row in snapshot.players if row.player_id is not None
        ] + selected_player_ids
        if len(assigned_player_ids) != len(set(assigned_player_ids)):
            raise ValueError("one player cannot resolve multiple official roster rows")
        for row in snapshot.players:
            if row.player_id is not None:
                player = db.get(Player, row.player_id)
                team_id = match.home_team_id if row.side == "home" else match.away_team_id
                if player is None or player.team_id != team_id:
                    raise ValueError("linked roster player does not belong to the fixture side")
                PDFService._upsert_roster_entries(db, fixture, match, row, player)
        for snapshot_player_id, resolution in requested.items():
            row = snapshot_players.get(snapshot_player_id)
            if row is None:
                raise ValueError("roster row does not belong to this fixture")
            team_id = match.home_team_id if row.side == "home" else match.away_team_id
            if resolution.existing_player_id is not None:
                player = db.get(Player, resolution.existing_player_id)
                if player is None or player.team_id != team_id:
                    raise ValueError("selected player does not belong to the fixture side")
            else:
                player = Player(name=row.name, team_id=team_id, default_jersey_number=row.jersey_number)
                db.add(player); db.flush()
            row.player_id = player.id
            PDFService._upsert_roster_entries(db, fixture, match, row, player)
        db.flush()
        if not PDFService._roster_is_ready(db, fixture, snapshot):
            raise ValueError("official roster projection is incomplete or inconsistent")
        db.commit()
        remaining = db.query(OfficialSnapshotPlayer).filter_by(snapshot_id=snapshot.id, player_id=None).count()
        db.refresh(snapshot)
        return {"match_id": match.id, "roster_status": "ready" if PDFService._roster_is_ready(db, fixture, snapshot) else "needs_identity_resolution", "unresolved_roster_players": remaining}

    @staticmethod
    def _confirmed_snapshot(fixture: ScheduledMatch) -> OfficialSnapshot | None:
        return next(
            (item for item in (fixture.analysis_match.official_snapshots if fixture.analysis_match else []) if item.is_confirmed),
            None,
        )

    @staticmethod
    def _roster_is_ready(db: Session, fixture: ScheduledMatch, snapshot: OfficialSnapshot) -> bool:
        match = fixture.analysis_match
        if match is None or snapshot.match_id != match.id or not snapshot.is_confirmed:
            return False
        if any(row.player_id is None or row.side not in {"home", "away"} for row in snapshot.players):
            return False
        player_ids = [row.player_id for row in snapshot.players]
        if len(player_ids) != len(set(player_ids)):
            return False
        for row in snapshot.players:
            team_id = match.home_team_id if row.side == "home" else match.away_team_id
            registration_id = fixture.home_registration_id if row.side == "home" else fixture.away_registration_id
            player = db.get(Player, row.player_id)
            if player is None or player.team_id != team_id:
                return False
            squad_count = db.query(MatchSquad).filter_by(
                match_id=match.id, player_id=row.player_id, jersey_number=row.jersey_number,
            ).count()
            stage_count = db.query(StageRoster).filter_by(
                registration_id=registration_id, player_id=row.player_id, jersey_number=row.jersey_number,
            ).count()
            if squad_count != 1 or stage_count != 1:
                return False
        return True

    @staticmethod
    def _identity_candidates(db: Session, team_id: int | None, name: str) -> list[Player]:
        if team_id is None:
            return []
        normalized = PDFService._normalize_identity_name(name)
        return [player for player in db.query(Player).filter_by(team_id=team_id).order_by(Player.id).all()
                if PDFService._normalize_identity_name(player.name) == normalized]

    @staticmethod
    def _normalize_identity_name(name: str) -> str:
        import unicodedata
        return " ".join("".join(char for char in unicodedata.normalize("NFD", name) if not unicodedata.combining(char)).casefold().split())

    @staticmethod
    def _upsert_roster_entries(db: Session, fixture: ScheduledMatch, match: Match, row: OfficialSnapshotPlayer, player: Player) -> None:
        squad = db.query(MatchSquad).filter_by(match_id=match.id, player_id=player.id).one_or_none()
        values = {key: getattr(row, key) for key in ("official_goals", "official_yellow", "official_2min", "official_red", "official_blue")}
        if squad is None:
            db.add(MatchSquad(match_id=match.id, player_id=player.id, jersey_number=row.jersey_number, **values))
        elif squad.jersey_number != row.jersey_number:
            raise ValueError(f"player {player.id} is already in MatchSquad with jersey {squad.jersey_number}; cannot assign jersey {row.jersey_number}")
        else:
            for key, value in values.items():
                setattr(squad, key, value)

        registration_id = fixture.home_registration_id if row.side == "home" else fixture.away_registration_id

        existing_stage_roster_for_player = db.query(StageRoster).filter_by(
            registration_id=registration_id, player_id=player.id
        ).filter(
            StageRoster.jersey_number != row.jersey_number
        ).one_or_none()
        if existing_stage_roster_for_player:
            raise ValueError(f"player {player.id} is already assigned to jersey {existing_stage_roster_for_player.jersey_number} in stage roster for registration {registration_id}; cannot assign jersey {row.jersey_number}")

        stage_row_entry = db.query(StageRoster).filter_by(registration_id=registration_id, jersey_number=row.jersey_number).one_or_none()
        if stage_row_entry is None:
            db.add(StageRoster(registration_id=registration_id, player_id=player.id, jersey_number=row.jersey_number))
        elif stage_row_entry.player_id != player.id:
            raise ValueError("fixture jersey is already assigned to another stage roster player")

    @staticmethod
    def fixture_preview(db: Session, fixture_key: str, file_bytes: bytes, filename: str, content_type: str | None) -> dict:
        fixture = PDFService._fixture(db, fixture_key)
        preview = PDFService.preview_femebal_sheet(file_bytes, filename, content_type)
        home = PDFService._compatibility(fixture.home_registration, preview["home_team"]["name"])
        away = PDFService._compatibility(fixture.away_registration, preview["away_team"]["name"])
        scores = (fixture.source_home_score, fixture.source_away_score, preview["match_info"].get("home_score"), preview["match_info"].get("away_score"))
        reconciliation = "unknown" if any(value is None for value in scores) else "match" if scores[:2] == scores[2:] else "mismatch"
        return {"fixture": PDFService.fixture_read(fixture), "preview": preview,
                "home_compatibility": home, "away_compatibility": away,
                "score_reconciliation": reconciliation}

    @staticmethod
    def match_preview(db: Session, match_id: int, file_bytes: bytes, filename: str, content_type: str | None) -> dict:
        match = db.query(Match).options(joinedload(Match.home_team), joinedload(Match.away_team)).get(match_id)
        if match is None:
            raise ValueError("Partido no encontrado")
        if match.origin != "manual":
            raise ValueError("Esta operación solo está disponible para partidos manuales")
        preview = PDFService.preview_femebal_sheet(file_bytes, filename, content_type)
        def compatibility(team, parsed_name):
            if team is None:
                return {"status": "unresolved", "expected_name": None, "parsed_name": parsed_name or None}
            equal = PDFService._normalize_identity_name(team.name) == PDFService._normalize_identity_name(parsed_name or "")
            return {"status": "compatible" if equal else "incompatible", "expected_name": team.name, "parsed_name": parsed_name or None}
        parsed_home, parsed_away = preview["match_info"].get("home_score"), preview["match_info"].get("away_score")
        # Manual matches begin without an official result. The legacy 0-0 column
        # defaults must not be treated as a declared score before a sheet exists.
        unreported_manual_score = match.origin == "manual" and (match.home_score, match.away_score) == (0, 0)
        score = "unknown" if unreported_manual_score or None in (match.home_score, match.away_score, parsed_home, parsed_away) else "match" if (match.home_score, match.away_score) == (parsed_home, parsed_away) else "mismatch"
        parsed_date = preview["match_info"].get("date")
        parsed_date_value = date.fromisoformat(parsed_date) if isinstance(parsed_date, str) else None
        date_status = "unknown" if match.date is None or parsed_date_value is None else "match" if match.date == parsed_date_value else "mismatch"
        warnings = list(preview["warnings"])
        if score == "mismatch": warnings.append("El marcador de la planilla no coincide con el partido manual.")
        if date_status == "mismatch": warnings.append("La fecha de la planilla no coincide con el partido manual.")
        if any(item["status"] == "incompatible" for item in (compatibility(match.home_team, preview["home_team"]["name"]), compatibility(match.away_team, preview["away_team"]["name"]))):
            warnings.append("Los equipos de la planilla no coinciden con el partido manual.")
        return {
            "match_id": match.id, "preview": preview,
            "home_compatibility": compatibility(match.home_team, preview["home_team"]["name"]),
            "away_compatibility": compatibility(match.away_team, preview["away_team"]["name"]),
            "score_reconciliation": score, "date_reconciliation": date_status, "warnings": warnings,
        }

    @staticmethod
    def confirm_match_pdf(db: Session, match_id: int, file_bytes: bytes, filename: str,
                          content_type: str | None, confirmation: MatchPDFConfirmation) -> dict:
        # Serialize confirmations per match. PostgreSQL holds this lock until the
        # transaction commits, so a concurrent request rechecks the committed sheet.
        match = db.query(Match).filter(Match.id == match_id).with_for_update().one_or_none()
        if match is None:
            raise ValueError("Partido no encontrado")
        if match.origin != "manual":
            raise ValueError("Esta operación solo está disponible para partidos manuales")
        existing = PDFService.official_sheet(db, match_id)
        if existing:
            return {"match_id": match_id, "snapshot_id": existing.id, "reused": True}
        if match.home_team_id is None or match.away_team_id is None:
            raise ValueError("El partido debe tener equipos definidos antes de confirmar la planilla")
        context = PDFService.match_preview(db, match_id, file_bytes, filename, content_type)
        mismatches = (
            context["score_reconciliation"] == "mismatch"
            or context["date_reconciliation"] == "mismatch"
            or any(context[key]["status"] == "incompatible" for key in ("home_compatibility", "away_compatibility"))
        )
        if mismatches and not confirmation.acknowledge_mismatches:
            raise ValueError("Debe reconocer explícitamente las discrepancias de la planilla")
        PDFService._validate_match_roster(context["preview"], confirmation)
        PDFService._fixture_players(db, match.home_team_id, confirmation.home_players)
        PDFService._fixture_players(db, match.away_team_id, confirmation.away_players)
        info = context["preview"]["match_info"]
        if not isinstance(info.get("home_score"), int) or not isinstance(info.get("away_score"), int):
            raise ValueError("La planilla debe incluir ambos marcadores")
        parsed_date = info.get("date")
        if match.date is None and not parsed_date:
            raise ValueError("El partido manual y la planilla no informan una fecha")
        confirmed_date = match.date or date.fromisoformat(parsed_date)
        snapshot_id, source_path = str(uuid.uuid4()), None
        try:
            source_path = PDFService.save_pdf(file_bytes, filename, snapshot_id)
            provenance = context["preview"]["provenance"]
            snapshot = OfficialSnapshot(
                id=snapshot_id, match_id=match.id, source_path=source_path, confirmed_date=confirmed_date,
                home_team_name=context["preview"]["home_team"]["name"], away_team_name=context["preview"]["away_team"]["name"],
                home_score=info["home_score"], away_score=info["away_score"],
                **{f"source_{key}": value for key, value in provenance.items()},
            )
            db.add(snapshot)
            PDFService._fixture_snapshot_players(db, match, snapshot, "home", match.home_team_id, confirmation.home_players)
            PDFService._fixture_snapshot_players(db, match, snapshot, "away", match.away_team_id, confirmation.away_players)
            db.commit()
        except Exception:
            db.rollback()
            if source_path and os.path.exists(source_path): os.remove(source_path)
            raise
        return {"match_id": match.id, "snapshot_id": snapshot.id, "reused": False}

    @staticmethod
    def confirm_fixture(db: Session, fixture_key: str, file_bytes: bytes, filename: str,
                        content_type: str | None, confirmation: FixtureConfirmation) -> dict:
        existing_fixture = PDFService._fixture(db, fixture_key)
        if existing_fixture.analysis_match and existing_fixture.analysis_match.official_snapshots:
            snapshot = existing_fixture.analysis_match.official_snapshots[0]
            return {"match_id": existing_fixture.analysis_match.id, "snapshot_id": snapshot.id, "reused": True}
        context = PDFService.fixture_preview(db, fixture_key, file_bytes, filename, content_type)
        if any(context[side]["status"] == "incompatible" for side in ("home_compatibility", "away_compatibility")):
            if not confirmation.acknowledge_name_mismatch:
                raise ValueError("La planilla no coincide con las inscripciones del fixture (diferencia en nombres de equipos)")
        if context["score_reconciliation"] == "mismatch" and not confirmation.acknowledge_score_mismatch:
            raise ValueError("Debe confirmar la discrepancia de marcador")
        fixture = PDFService._fixture(db, fixture_key)
        home = PDFService._existing_team(db, confirmation.home_team_id)
        away = PDFService._existing_team(db, confirmation.away_team_id)
        if home.id == away.id:
            raise ValueError("Los equipos confirmados deben ser distintos")
        PDFService._validate_fixture_roster(context["preview"], confirmation)
        PDFService._fixture_players(db, home.id, confirmation.home_players)
        PDFService._fixture_players(db, away.id, confirmation.away_players)
        if fixture.analysis_match:
            snapshot = fixture.analysis_match.official_snapshots[0]
            return {"match_id": fixture.analysis_match.id, "snapshot_id": snapshot.id, "reused": True}
        info = context["preview"]["match_info"]
        if not isinstance(info.get("home_score"), int) or not isinstance(info.get("away_score"), int):
            raise ValueError("La planilla debe incluir ambos marcadores")
        confirmed_date = fixture.scheduled_date or date.fromisoformat(info["date"])
        snapshot_id, source_path = str(uuid.uuid4()), None
        try:
            match = Match(date=confirmed_date, home_team_id=home.id, away_team_id=away.id,
                          home_score=info["home_score"], away_score=info["away_score"],
                          scheduled_match_id=fixture.id, origin="fixture")
            db.add(match); db.flush()
            source_path = PDFService.save_pdf(file_bytes, filename, snapshot_id)
            provenance = context["preview"]["provenance"]
            snapshot = OfficialSnapshot(id=snapshot_id, match_id=match.id, source_path=source_path,
                confirmed_date=confirmed_date, home_team_name=context["preview"]["home_team"]["name"],
                away_team_name=context["preview"]["away_team"]["name"], home_score=info["home_score"], away_score=info["away_score"],
                **{f"source_{key}": value for key, value in provenance.items()})
            db.add(snapshot)
            PDFService._fixture_snapshot_players(db, match, snapshot, "home", home.id, confirmation.home_players)
            PDFService._fixture_snapshot_players(db, match, snapshot, "away", away.id, confirmation.away_players)
            db.commit()
        except IntegrityError:
            db.rollback()
            if source_path and os.path.exists(source_path): os.remove(source_path)
            existing = db.query(Match).options(joinedload(Match.official_snapshots)).filter_by(scheduled_match_id=fixture.id).one_or_none()
            if existing and existing.official_snapshots:
                return {"match_id": existing.id, "snapshot_id": existing.official_snapshots[0].id, "reused": True}
            raise
        except Exception:
            db.rollback()
            if source_path and os.path.exists(source_path): os.remove(source_path)
            raise
        return {"match_id": match.id, "snapshot_id": snapshot.id, "reused": False}

    @staticmethod
    def _fixture(db: Session, fixture_key: str) -> ScheduledMatch:
        fixture = db.query(ScheduledMatch).join(FixtureImportEntry).filter(
            ScheduledMatch.fixture_key == fixture_key, FixtureImportEntry.kind == "match"
).options(joinedload(ScheduledMatch.home_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
                   joinedload(ScheduledMatch.away_registration).joinedload(TeamRegistration.competition_team).joinedload(CompetitionTeam.club),
                  joinedload(ScheduledMatch.stage).joinedload(TournamentStage.season),
                  joinedload(ScheduledMatch.analysis_match).joinedload(Match.official_snapshots)).first()
        if fixture is None: raise ValueError("El fixture no existe o es un bye")
        return fixture

    @staticmethod
    def _compatibility(registration, parsed_name: str) -> dict:
        expected, variant = registration.competition_team.club.name, registration.competition_team.variant
        parsed_variant = parsed_name.strip().split()[-1].upper() if parsed_name.strip() else None
        normalized = lambda value: "".join(char for char in value.lower() if char.isalnum()).removeprefix("ca")
        base = parsed_name.rsplit(" ", 1)[0] if variant and parsed_variant == variant.upper() else parsed_name
        status = "unresolved" if not parsed_name else "compatible" if normalized(base) == normalized(expected) and (not variant or parsed_variant == variant.upper()) else "incompatible"
        return {"status": status, "expected_name": expected, "expected_variant": variant,
                "parsed_name": parsed_name or None, "parsed_variant": parsed_variant if variant else None}

    @staticmethod
    def _existing_team(db: Session, team_id: int) -> Team:
        team = db.get(Team, team_id)
        if team is None: raise ValueError("El equipo confirmado no existe")
        return team

    @staticmethod
    def _get_or_create_team_by_club(db: Session, club_name: str) -> Team:
        """Find existing Team by club_name or create new one."""
        team = db.query(Team).filter(Team.club_name == club_name).first()
        if team is None:
            team = Team(name=club_name, club_name=club_name)
            db.add(team)
            db.flush()
        return team

    @staticmethod
    def _fixture_players(db: Session, team_id: int, players) -> None:
        for confirmed in players:
            if confirmed.existing_player_id is None:
                continue
            player = db.get(Player, confirmed.existing_player_id)
            if player is None or player.team_id != team_id: raise ValueError("El jugador confirmado no pertenece al equipo confirmado")

    @staticmethod
    def _resolve_confirmed_player(db: Session, team_id: int, confirmed) -> Player:
        if confirmed.existing_player_id is not None:
            player = db.get(Player, confirmed.existing_player_id)
            if player is None or player.team_id != team_id:
                raise ValueError("El jugador confirmado no pertenece al equipo confirmado")
            return player
        normalized_name = PDFService._normalize_identity_name(confirmed.name)
        for player in db.query(Player).filter(Player.team_id == team_id).all():
            if PDFService._normalize_identity_name(player.name) == normalized_name:
                return player
        player = Player(name=confirmed.name, team_id=team_id, default_jersey_number=confirmed.jersey_number)
        db.add(player)
        db.flush()
        return player

    @staticmethod
    def _fixture_snapshot_players(db: Session, match, snapshot, side, team_id, players) -> None:
        for confirmed in players:
            values = {key: getattr(confirmed, key) for key in ("official_goals", "official_yellow", "official_2min", "official_red", "official_blue")}
            player = PDFService._resolve_confirmed_player(db, team_id, confirmed)
            if not db.query(MatchSquad).filter(MatchSquad.match_id == match.id, MatchSquad.player_id == player.id).first():
                db.add(MatchSquad(match_id=match.id, player_id=player.id, jersey_number=confirmed.jersey_number, **values))
            db.add(OfficialSnapshotPlayer(snapshot_id=snapshot.id, side=side, player_id=player.id,
                   name=confirmed.name, jersey_number=confirmed.jersey_number, **values))

    @staticmethod
    def reconcile_snapshot_players(db: Session, match_id: int) -> int:
        match = db.query(Match).filter(Match.id == match_id).one_or_none()
        snapshot = PDFService.official_sheet(db, match_id)
        if match is None or snapshot is None:
            raise ValueError("Partido o planilla oficial no encontrados")
        repaired = 0
        for row in snapshot.players:
            if row.player_id is not None:
                continue
            team_id = match.home_team_id if row.side == "home" else match.away_team_id
            if team_id is None:
                raise ValueError("La planilla no puede vincular jugadores sin equipos definidos")
            class ConfirmedPlayer:
                existing_player_id = None
                name = row.name
                jersey_number = row.jersey_number
            player = PDFService._resolve_confirmed_player(db, team_id, ConfirmedPlayer)
            row.player_id = player.id
            if not db.query(MatchSquad).filter(MatchSquad.match_id == match.id, MatchSquad.player_id == player.id).first():
                db.add(MatchSquad(match_id=match.id, player_id=player.id, jersey_number=row.jersey_number,
                                  official_goals=row.official_goals, official_yellow=row.official_yellow,
                                  official_2min=row.official_2min, official_red=row.official_red,
                                  official_blue=row.official_blue))
            repaired += 1
        if repaired:
            db.commit()
        return repaired

    @staticmethod
    def _validate_fixture_roster(preview: dict, confirmation: FixtureConfirmation) -> None:
        fields = ("name", "jersey_number", "official_goals", "official_yellow", "official_2min", "official_red", "official_blue")
        for preview_side, confirmation_players in (
            ("home_team", confirmation.home_players),
            ("away_team", confirmation.away_players),
        ):
            expected = [
                (player["name"], player["number"], player["goals"], player["yellow"], player["two_min"], player["red"], player["blue"])
                for player in preview[preview_side]["players"]
            ]
            received = [tuple(getattr(player, field) for field in fields) for player in confirmation_players]
            if received != expected:
                raise ValueError("Los jugadores confirmados deben coincidir con los jugadores parseados de la planilla")

    @staticmethod
    def _validate_match_roster(preview: dict, confirmation: MatchPDFConfirmation) -> None:
        fields = ("name", "jersey_number", "official_goals", "official_yellow", "official_2min", "official_red", "official_blue")
        for preview_side, confirmation_players in (("home_team", confirmation.home_players), ("away_team", confirmation.away_players)):
            expected = [(player["name"], player["number"], player["goals"], player["yellow"], player["two_min"], player["red"], player["blue"]) for player in preview[preview_side]["players"]]
            received = [tuple(getattr(player, field) for field in fields) for player in confirmation_players]
            if received != expected:
                raise ValueError("Los jugadores confirmados deben coincidir con los jugadores parseados de la planilla")

    @staticmethod
    def confirm_import(
        db: Session,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        confirmation: PDFImportConfirmation,
    ) -> OfficialSnapshot:
        provenance = PDFService.preview_femebal_sheet(file_bytes, filename, content_type)["provenance"]
        snapshot_id = str(uuid.uuid4())
        home_team = PDFService._confirmed_team(db, confirmation.home_team)
        away_team = PDFService._confirmed_team(db, confirmation.away_team)
        if home_team.id == away_team.id:
            raise ValueError("Los equipos confirmados deben ser distintos")

        match = Match(
            date=confirmation.date,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=confirmation.home_score,
            away_score=confirmation.away_score,
            origin="fixture",
        )
        db.add(match)
        db.flush()
        source_path = PDFService.save_pdf(file_bytes, filename, snapshot_id)
        snapshot = OfficialSnapshot(
            id=snapshot_id,
            match_id=match.id,
            source_path=source_path,
            confirmed_date=confirmation.date,
            home_team_name=confirmation.home_team.name,
            away_team_name=confirmation.away_team.name,
            home_score=confirmation.home_score,
            away_score=confirmation.away_score,
            **{f"source_{key}": value for key, value in provenance.items()},
        )
        db.add(snapshot)
        PDFService._confirmed_players(db, match, snapshot, "home", home_team.id, confirmation.home_players)
        PDFService._confirmed_players(db, match, snapshot, "away", away_team.id, confirmation.away_players)
        try:
            db.commit()
        except Exception:
            if os.path.exists(source_path):
                os.remove(source_path)
            raise
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def _confirmed_team(db: Session, confirmed: PDFConfirmedTeam) -> Team:
        if confirmed.existing_team_id is not None:
            team = db.get(Team, confirmed.existing_team_id)
            if team is None:
                raise ValueError("El equipo confirmado no existe")
            return team
        team = Team(name=confirmed.name)
        db.add(team)
        db.flush()
        return team

    @staticmethod
    def _confirmed_players(
        db: Session, match: Match, snapshot: OfficialSnapshot, side: str, team_id: int,
        confirmed_players: list[PDFConfirmedPlayer],
    ) -> None:
        for confirmed in confirmed_players:
            if confirmed.existing_player_id is not None:
                player = db.get(Player, confirmed.existing_player_id)
                if player is None or player.team_id != team_id:
                    raise ValueError("El jugador confirmado no pertenece al equipo confirmado")
            else:
                player = Player(
                    name=confirmed.name,
                    team_id=team_id,
                    default_jersey_number=confirmed.jersey_number,
                )
                db.add(player)
                db.flush()
            values = {
                "official_goals": confirmed.official_goals,
                "official_yellow": confirmed.official_yellow,
                "official_2min": confirmed.official_2min,
                "official_red": confirmed.official_red,
                "official_blue": confirmed.official_blue,
            }
            db.add(MatchSquad(match_id=match.id, player_id=player.id, jersey_number=confirmed.jersey_number, **values))
            db.add(OfficialSnapshotPlayer(snapshot_id=snapshot.id, side=side, player_id=player.id, name=confirmed.name, jersey_number=confirmed.jersey_number, **values))

    @staticmethod
    def preview_femebal_sheet(file_bytes: bytes, filename: str, content_type: str | None) -> dict:
        if len(file_bytes) > PDFService.MAX_SIZE_BYTES:
            raise PDFParseError("El PDF supera el limite de 10 MB")
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                page_count = len(pdf.pages)
        except Exception as error:
            raise PDFParseError("No se pudo leer el PDF de planilla") from error
        if page_count > PDFService.MAX_PAGES:
            raise PDFParseError("El PDF supera el limite de 10 paginas")

        data = PDFService.parse_femebal_sheet(io.BytesIO(file_bytes))
        match_info = data["match_info"]
        warnings = list(data["warnings"])

        if not data["home_team"]["name"] or not data["away_team"]["name"]:
            warnings.append("No se pudieron identificar ambos equipos")
        if "home_score" not in match_info or "away_score" not in match_info:
            warnings.append("No se pudo identificar el marcador oficial")
        if not match_info.get("date"):
            warnings.append("No se pudo identificar la fecha del partido")
        if not data["home_team"]["players"] and not data["away_team"]["players"]:
            warnings.append("No se pudieron identificar jugadores en la planilla")

        data["provenance"] = {
            "filename": filename,
            "content_type": content_type or "application/pdf",
            "size_bytes": len(file_bytes),
            "sha256": hashlib.sha256(file_bytes).hexdigest(),
            "page_count": page_count,
        }
        data["warnings"] = list(dict.fromkeys(warnings))
        return data

    @staticmethod
    def parse_femebal_sheet(pdf_file):
        data = {
            "match_info": {},
            "home_team": {"name": "", "players": []},
            "away_team": {"name": "", "players": []},
            "fields": {},
            "warnings": [],
        }

        with pdfplumber.open(pdf_file) as pdf:
            page_data = [
                (page.extract_tables(), page.extract_text(), page_number)
                for page_number, page in enumerate(pdf.pages, start=1)
            ]
            word_pages = {
                page_number: page.extract_words(use_text_flow=True)
                for page_number, page in enumerate(pdf.pages, start=1)
                if hasattr(page, "extract_words")
            }
            header = parse_header_pages(page_data, word_pages) if word_pages else parse_header_pages(page_data)
            fields = header["fields"]
            data["fields"] = fields
            data["warnings"] = header["warnings"]
            data["match_info"] = {
                field: fields[field]["value"]
                for field in ("tournament", "venue", "court", "date", "time", "category", "match_number", "home_score", "away_score")
                if fields[field]["value"] is not None
            }
            data["home_team"]["name"] = fields["home_name"]["value"] or ""
            data["away_team"]["name"] = fields["away_name"]["value"] or ""

            for tables, _, page_number in page_data:
                PDFService._append_page_players(data, tables, page_number)

        return data

    @staticmethod
    def _append_page_players(data, tables, page_number):
        players_table = next(
            (
                table for table in tables
                if any(
                    "local" in row_text and "visitante" in row_text and "n°" in row_text
                    for row_text in (
                        " ".join(str(cell) for cell in row if cell).lower()
                        for row in table[:3]
                    )
                )
            ),
            max(tables, key=len) if tables else None,
        )
        if not players_table:
            return

        start_row_index = next(
            (index + 1 for index, row in enumerate(players_table)
             if "n°" in " ".join(str(cell) for cell in row if cell).lower()),
            0,
        )
        for row in players_table[start_row_index:]:
            if len(row) < 7:
                continue
            for side, offset in (("home_team", 0), ("away_team", 7)):
                if len(row) < offset + 7 or not row[offset] or not row[offset + 1]:
                    continue
                player = PDFService._parse_player_row(row[offset:offset + 7])
                if player:
                    player["source"] = {"page": page_number}
                    data[side]["players"].append(player)

    @staticmethod
    def _parse_player_row(row):
        try:
            if not row[0]:
                return None
            number = str(row[0]).strip()
            if not number.isdigit():
                return None
            if not row[1]:
                return None
            name = str(row[1]).strip()
            goals = PDFService._clean_int(row[2])
            yellow = 1 if row[3] and str(row[3]).strip() not in ["-", ""] else 0
            two_min = PDFService._clean_int(row[4])
            red = 1 if row[5] and str(row[5]).strip() not in ["-", ""] else 0
            blue = 1 if row[6] and str(row[6]).strip() not in ["-", ""] else 0
            return {
                "number": int(number),
                "name": name,
                "goals": goals,
                "yellow": yellow,
                "two_min": two_min,
                "red": red,
                "blue": blue,
            }
        except Exception:
            return None

    @staticmethod
    def _clean_int(val) -> int:
        if not val:
            return 0
        val = str(val).strip()
        if val in ["-", "", "None"]:
            return 0
        try:
            return int(val)
        except ValueError:
            return 0

    @staticmethod
    def _load_fixture_pdf_bytes(db: Session, fixture_key: str) -> tuple[bytes, str]:
        """
        Load PDF bytes for a fixture from the indexed planillas directory.
        Returns (file_bytes, filename).
        """
        # Find the fixture import entry for this fixture
        fixture_entry = db.query(FixtureImportEntry).join(ScheduledMatch).filter(
            ScheduledMatch.fixture_key == fixture_key,
            FixtureImportEntry.kind == "match"
        ).first()

        if fixture_entry is None:
            raise ValueError("El fixture no existe o es un bye")

        # Try to get the PDF path from raw_entry.planilla.path
        raw_entry = fixture_entry.raw_entry or {}
        pdf_path = None

        if isinstance(raw_entry, dict):
            planilla = raw_entry.get("planilla", {})
            if isinstance(planilla, dict):
                pdf_path = planilla.get("path")

        # If not in raw_entry, try to find by SHA256 in the index
        if not pdf_path:
            # Look for SHA256 in raw_entry
            sha256 = raw_entry.get("sha256") if isinstance(raw_entry, dict) else None
            if sha256:
                # Load index.json and find matching entry
                index_path = PLANILLAS_INDEXED_DIR / "index.json"
                if index_path.exists():
                    with open(index_path, "r", encoding="utf-8") as f:
                        index_data = json.load(f)
                    for entry in index_data.get("entries", []):
                        if entry.get("sha256") == sha256:
                            pdf_path = entry.get("alias")
                            break

        if not pdf_path:
            raise ValueError("No se encontró el archivo PDF para este fixture")

        # Load PDF from resources/planillas/_indexed/
        full_path = PLANILLAS_INDEXED_DIR / pdf_path
        if not full_path.exists():
            raise ValueError(f"Archivo PDF no encontrado: {full_path}")

        with open(full_path, "rb") as f:
            file_bytes = f.read()

        return file_bytes, pdf_path
