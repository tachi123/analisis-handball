import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import FixtureImportEntry, User
from ...schemas import FixtureConfirmResult, FixtureConfirmation, FixturePreviewResult, FixtureRosterRead, FixtureRosterResolveRequest, FixtureRosterResolveResult, MatchPDFConfirmation, MatchPDFConfirmResult, MatchPDFPreviewResult, PDFImportConfirmation, PDFImportResult, PDFPreview, ScheduledFixtureRead
from ...services.pdf_service import PDFParseError, PDFService
from ...services.match_service import MatchService


router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.post("/matches/{match_id}/preview", response_model=MatchPDFPreviewResult)
async def preview_match_pdf(match_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        MatchService.require_manual_owner(db, match_id, _user)
        return PDFService.match_preview(db, match_id, await file.read(), file.filename or "", file.content_type)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (ValueError, PDFParseError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/matches/{match_id}/confirm", response_model=MatchPDFConfirmResult, status_code=201)
async def confirm_match_pdf(match_id: int, file: UploadFile = File(...), confirmation_json: str = Form(...), db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        MatchService.require_manual_owner(db, match_id, _user)
        confirmation = MatchPDFConfirmation.model_validate_json(confirmation_json)
        return PDFService.confirm_match_pdf(db, match_id, await file.read(), file.filename or "", file.content_type, confirmation)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (ValueError, json.JSONDecodeError, PDFParseError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/fixtures", response_model=list[ScheduledFixtureRead])
def list_fixtures(
    status: Optional[str] = Query(default="pending", pattern="^(pending|all)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    fixtures = PDFService.list_fixtures(db)
    if status == "pending":
        fixtures = [f for f in fixtures if f.result_status != "confirmed"]
    return [PDFService.fixture_read(fixture) for fixture in fixtures]


@router.get("/fixtures/{fixture_key}", response_model=ScheduledFixtureRead)
def select_preloaded_fixture(fixture_key: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        return PDFService.fixture_read(PDFService.preloaded_fixture(db, fixture_key))
    except ValueError as error:
        raise HTTPException(status_code=409, detail="no_confirmed_official_data") from error


@router.get("/fixtures/{fixture_key}/roster", response_model=FixtureRosterRead)
def get_fixture_roster(fixture_key: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        return PDFService.fixture_roster(db, fixture_key)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/fixtures/{fixture_key}/review", response_model=FixturePreviewResult)
def review_fixture_pdf(fixture_key: str, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    """
    Load PDF from indexed path and return preview with compatibility analysis.
    Rejects 409 if fixture is already confirmed or is a bye.
    """
    try:
        fixture = PDFService._fixture(db, fixture_key)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    # Reject if already confirmed
    if fixture.result_status == "confirmed":
        raise HTTPException(status_code=409, detail="fixture_already_confirmed")

    # Reject if bye
    fixture_entry = db.query(FixtureImportEntry).filter(
        FixtureImportEntry.scheduled_match_id == fixture.id,
        FixtureImportEntry.kind == "bye"
    ).first()
    if fixture_entry:
        raise HTTPException(status_code=404, detail="Fixture es un bye, no tiene planilla")

    # Load PDF bytes from indexed path
    try:
        file_bytes, filename = PDFService._load_fixture_pdf_bytes(db, fixture_key)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    # Call fixture_preview
    try:
        return PDFService.fixture_preview(db, fixture_key, file_bytes, filename, "application/pdf")
    except (ValueError, PDFParseError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/fixtures/{fixture_key}/review", response_model=FixtureConfirmResult, status_code=201)
def confirm_fixture_review(fixture_key: str, confirmation: FixtureConfirmation, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    """
    Confirm fixture using PDF from indexed path.
    Auto-fills home_team_id/away_team_id from fixture registrations.
    Returns {match_id, snapshot_id, reused: boolean}.
    """
    try:
        fixture = PDFService._fixture(db, fixture_key)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    # Reject if already confirmed
    if fixture.result_status == "confirmed":
        raise HTTPException(status_code=409, detail="fixture_already_confirmed")

    # Reject if bye
    fixture_entry = db.query(FixtureImportEntry).filter(
        FixtureImportEntry.scheduled_match_id == fixture.id,
        FixtureImportEntry.kind == "bye"
    ).first()
    if fixture_entry:
        raise HTTPException(status_code=404, detail="Fixture es un bye, no tiene planilla")

    # Auto-fill team IDs from fixture registrations (find or create Team by club name)
    home_club_name = fixture.home_registration.competition_team.club.name
    away_club_name = fixture.away_registration.competition_team.club.name
    home_team = PDFService._get_or_create_team_by_club(db, home_club_name)
    away_team = PDFService._get_or_create_team_by_club(db, away_club_name)
    if home_team.id == away_team.id:
        raise HTTPException(status_code=422, detail="Los equipos confirmados deben ser distintos")
    confirmation.home_team_id = home_team.id
    confirmation.away_team_id = away_team.id

    # Load PDF bytes from indexed path
    try:
        file_bytes, filename = PDFService._load_fixture_pdf_bytes(db, fixture_key)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    # Call confirm_fixture
    try:
        return PDFService.confirm_fixture(db, fixture_key, file_bytes, filename, "application/pdf", confirmation)
    except (ValueError, PDFParseError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/fixtures/{fixture_key}/roster-resolution", response_model=FixtureRosterResolveResult)
def resolve_fixture_roster(fixture_key: str, request: FixtureRosterResolveRequest, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    try:
        return PDFService.resolve_fixture_roster(db, fixture_key, request.resolutions)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/fixture-preview", response_model=FixturePreviewResult)
async def preview_fixture_pdf(fixture_key: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        return PDFService.fixture_preview(db, fixture_key, await file.read(), file.filename or "", file.content_type)
    except (ValueError, PDFParseError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/fixture-confirm", response_model=FixtureConfirmResult, status_code=201)
async def confirm_fixture_pdf(fixture_key: str = Form(...), file: UploadFile = File(...), confirmation_json: str = Form(...), db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    try:
        confirmation = FixtureConfirmation.model_validate_json(confirmation_json)
        return PDFService.confirm_fixture(db, fixture_key, await file.read(), file.filename or "", file.content_type, confirmation)
    except (ValueError, json.JSONDecodeError, PDFParseError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/parse", response_model=PDFPreview)
async def parse_pdf(file: UploadFile = File(...), _user: User = Depends(get_current_user)):
    """Devuelve una vista previa sin persistir datos oficiales ni identidades."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

    try:
        return PDFService.preview_femebal_sheet(
            await file.read(), file.filename, file.content_type
        )
    except PDFParseError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/confirm", response_model=PDFImportResult, status_code=201)
async def confirm_pdf(
    file: UploadFile = File(...),
    confirmation_json: str = Form(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("superadmin", "admin")),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    try:
        confirmation = PDFImportConfirmation.model_validate_json(confirmation_json)
        snapshot = PDFService.confirm_import(
            db, await file.read(), file.filename, file.content_type, confirmation
        )
        return PDFImportResult(match_id=snapshot.match_id, snapshot_id=snapshot.id)
    except (ValueError, json.JSONDecodeError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/import")
async def import_pdf(_user: User = Depends(require_role("superadmin", "admin"))):
    raise HTTPException(status_code=409, detail="Use /pdf/confirm con valores confirmados por el analista")
