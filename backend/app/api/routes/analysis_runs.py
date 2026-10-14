from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import Match, OfficialSnapshot, User
from ...schemas import AnalysisRun, AnalysisRunCreate
from ...services import analysis_run_service as service
from ...services.analysis_run_service import AnalysisRunError
from ...services.match_service import MatchService

router = APIRouter(tags=["analysis-runs"])


def _error(error: Exception):
    status_code = 403 if isinstance(error, PermissionError) else 404 if "not found" in str(error) else 409
    raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.get("/matches/{match_id}/analysis-runs", response_model=list[AnalysisRun])
def list_runs(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        return service.list_runs(db, match_id)
    except ValueError as error:
        _error(error)


@router.post("/matches/{match_id}/analysis-runs", response_model=AnalysisRun, status_code=201)
def create_run(match_id: int, data: AnalysisRunCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        match = db.query(Match).filter_by(id=match_id).one_or_none()
        if match is None:
            raise AnalysisRunError("match not found")
        if match.origin == "manual":
            MatchService.require_manual_owner(db, match_id, user)
        if not match.canonical_analysis_enabled:
            if not db.query(OfficialSnapshot).filter_by(match_id=match_id, is_confirmed=True).first():
                raise AnalysisRunError("a confirmed official sheet is required before creating an analysis run")
        return service.create_draft(db, match_id, data.mode, user)
    except (ValueError, PermissionError) as error:
        _error(error)


@router.post("/matches/{match_id}/analysis-runs/{run_id}/promote", response_model=AnalysisRun)
def promote_run(match_id: int, run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return service.promote(db, match_id, run_id, user)
    except (ValueError, PermissionError) as error:
        _error(error)
