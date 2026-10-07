from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import Match, OfficialSnapshot, User
from ...schemas import CanonicalCutoverUpdate, CanonicalEventCommand, CanonicalEventRevisionInput, CanonicalRecoveryRequest
from ...services import canonical_analysis_service as service
from ...services.match_service import MatchService

router = APIRouter(tags=["canonical-analysis"])


def _error(error: Exception):
    status_code = 403 if isinstance(error, PermissionError) else 404 if "not found" in str(error) else 409 if isinstance(error, service.CanonicalStateConflictError) or "disabled" in str(error) or "belongs to another analyst" in str(error) else 422
    raise HTTPException(status_code=status_code, detail=str(error)) from error


def _require_cutover(db: Session, match_id: int) -> None:
    try:
        service.require_canonical_cutover(db, match_id)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.post("/matches/{match_id}/canonical-events", status_code=201)
def create(match_id: int, data: CanonicalEventCommand, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return service.create_event(db, match_id, data, user.id)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.patch("/canonical-events/{event_id}")
def revise(event_id: int, data: CanonicalEventRevisionInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return service.revise_event(db, event_id, data, user.id)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.delete("/canonical-events/{event_id}")
def deactivate(event_id: int, reason: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return service.deactivate_event(db, event_id, reason, user.id)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.delete("/matches/{match_id}/canonical-events/last")
def deactivate_last(match_id: int, data: CanonicalRecoveryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return service.deactivate_last_event(db, match_id, data.reason, user.id)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.post("/matches/{match_id}/canonical-analysis/reset")
def reset_review(match_id: int, data: CanonicalRecoveryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return service.reset_analyst_review(db, match_id, data.reason, user.id)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.get("/matches/{match_id}/canonical-events")
def events(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _require_cutover(db, match_id)
    return service.read_events(db, match_id)


@router.get("/matches/{match_id}/canonical-state")
def state(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _require_cutover(db, match_id)
    return service.read_state(db, match_id)


@router.get("/matches/{match_id}/canonical-metrics")
def metrics(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _require_cutover(db, match_id)
    return service.read_metrics(db, match_id)


@router.get("/matches/{match_id}/canonical-reconciliation")
def reconciliation(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _require_cutover(db, match_id)
    return service.read_reconciliation(db, match_id)


@router.get("/matches/{match_id}/warnings-summary")
def warnings_summary(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    _require_cutover(db, match_id)
    return service.read_warnings_summary(db, match_id)


@router.get("/matches/{match_id}/canonical-player-projection")
def player_projection(match_id: int, player_id: int, team_id: int | None = None, period: int | None = None,
                      from_regulation_seconds: float | None = None, to_regulation_seconds: float | None = None,
                      db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        return service.read_player_projection(db, match_id, player_id, team_id=team_id, period=period,
                                              from_regulation_seconds=from_regulation_seconds,
                                              to_regulation_seconds=to_regulation_seconds)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.get("/matches/{match_id}/canonical-legacy-dry-run")
def dry_run(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return service.legacy_dry_run(db, match_id)


@router.put("/matches/{match_id}/canonical-cutover")
def set_cutover(match_id: int, data: CanonicalCutoverUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="match not found")
    if match.origin == "manual":
        try:
            MatchService.require_manual_owner(db, match_id, user)
        except (ValueError, PermissionError) as error:
            _error(error)
    if data.enabled and not db.query(OfficialSnapshot).filter_by(match_id=match_id, is_confirmed=True).first():
        raise HTTPException(status_code=422, detail="a confirmed official sheet is required before canonical analysis can start")
    if not data.enabled and user.role not in {"superadmin", "admin"}:
        raise HTTPException(status_code=403, detail="No tenés permiso para esta acción")
    match.canonical_analysis_enabled = data.enabled
    db.commit()
    return {"match_id": match_id, "canonical_analysis_enabled": match.canonical_analysis_enabled, "reason": data.reason}
