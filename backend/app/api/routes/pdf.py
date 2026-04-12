import io
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...services.pdf_service import PDFService
from ...services.match_service import MatchService
from ...services.team_service import TeamService
from ...services.player_service import PlayerService
from ...schemas import MatchCreate, TeamCreate, PlayerCreate, MatchSquadCreate

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.post("/parse")
async def parse_pdf(file: UploadFile = File(...), _user: User = Depends(get_current_user)):
    """Parsea una planilla Femebal y devuelve los datos sin persistir nada."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    contents = await file.read()
    data = PDFService.parse_femebal_sheet(io.BytesIO(contents))
    return data


@router.post("/import")
async def import_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("superadmin", "admin")),
):
    """Parsea una planilla Femebal y crea/actualiza el partido en la base de datos."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

    contents = await file.read()
    data = PDFService.parse_femebal_sheet(io.BytesIO(contents))
    match_info = data.get("match_info", {})

    # Resolve or create home team
    home_team_name = data["home_team"].get("name", "").strip()
    away_team_name = data["away_team"].get("name", "").strip()

    home_team = next((t for t in TeamService.get_all(db) if t.name == home_team_name), None)
    if not home_team and home_team_name:
        home_team = TeamService.create(db, TeamCreate(name=home_team_name))

    away_team = next((t for t in TeamService.get_all(db) if t.name == away_team_name), None)
    if not away_team and away_team_name:
        away_team = TeamService.create(db, TeamCreate(name=away_team_name))

    # Save PDF file
    file_path = PDFService.save_pdf(contents, file.filename)

    # Parse date
    from datetime import date as date_type
    raw_date = match_info.get("date", "")
    try:
        parsed_date = date_type.fromisoformat(raw_date)
    except (ValueError, TypeError):
        parsed_date = date_type.today()

    # Create match
    match_data = MatchCreate(
        date=parsed_date,
        home_team_id=home_team.id if home_team else None,
        away_team_id=away_team.id if away_team else None,
        venue=match_info.get("venue"),
        court=match_info.get("court"),
        match_time=match_info.get("time"),
        category_label=match_info.get("category"),
        match_number_label=str(match_info.get("match_number", "")),
        home_score=int(match_info.get("home_score", 0)),
        away_score=int(match_info.get("away_score", 0)),
        pdf_file_path=file_path,
    )
    match = MatchService.create(db, match_data)

    # Add players to squad
    for team_key, team_obj in [("home_team", home_team), ("away_team", away_team)]:
        if not team_obj:
            continue
        for p_data in data[team_key]["players"]:
            # Find or create global player
            all_players = PlayerService.get_by_team(db, team_obj.id)
            player = next((p for p in all_players if p.name == p_data["name"]), None)
            if not player:
                player = PlayerService.create(
                    db,
                    PlayerCreate(
                        name=p_data["name"],
                        default_jersey_number=p_data["number"],
                        global_position=None,
                        team_id=team_obj.id,
                    ),
                )
            # Upsert squad entry with official stats from PDF
            MatchService.upsert_squad_player(
                db,
                MatchSquadCreate(
                    match_id=match.id,
                    player_id=player.id,
                    jersey_number=p_data["number"],
                    official_goals=p_data["goals"],
                    official_yellow=p_data["yellow"],
                    official_2min=p_data["two_min"],
                    official_red=p_data["red"],
                    official_blue=p_data["blue"],
                ),
            )

    return MatchService.get_by_id(db, match.id)
