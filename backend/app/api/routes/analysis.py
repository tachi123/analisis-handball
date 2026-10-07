from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import User
from ...schemas import AnalysisSession, AnalysisSessionUpdate
from ...services.analysis_session_service import AnalysisSessionService

router = APIRouter(tags=["analysis"])


@router.get("/matches/{match_id}/analysis-session", response_model=AnalysisSession)
def get_session(match_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = AnalysisSessionService.get(db, match_id, user)
    if session is None:
        raise HTTPException(status_code=404, detail="Analysis session not found")
    return session


@router.put("/matches/{match_id}/analysis-session", response_model=AnalysisSession)
def save_session(match_id: int, data: AnalysisSessionUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return AnalysisSessionService.save(db, match_id, data, user)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
