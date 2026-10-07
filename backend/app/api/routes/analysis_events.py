from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import User
from ...schemas import AnalysisEvent, AnalysisEventCreate, AnalysisEventRevision, AnalysisEventUpdate
from ...services.analysis_service import AnalysisService
from ...services.analysis_event_service import AnalysisEventService

router = APIRouter(tags=["analysis-events"])


@router.get("/matches/{match_id}/analysis-events", response_model=List[AnalysisEvent])
def list_events(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return AnalysisEventService.get_by_match(db, match_id)


@router.get("/matches/{match_id}/reviewed-metrics")
def reviewed_metrics(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return AnalysisService.reviewed_metrics(db, match_id)


@router.post("/matches/{match_id}/analysis-events", response_model=AnalysisEvent, status_code=201)
def create_event(match_id: int, data: AnalysisEventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return AnalysisEventService.create(db, match_id, data, user)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/analysis-events/{event_id}", response_model=AnalysisEvent)
def update_event(event_id: int, data: AnalysisEventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = AnalysisEventService.get(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Analysis event not found")
    try:
        return AnalysisEventService.update(db, event, data, user)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/analysis-events/{event_id}", response_model=AnalysisEvent)
def delete_event(event_id: int, reason: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = AnalysisEventService.get(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Analysis event not found")
    return AnalysisEventService.set_active(db, event, False, reason, user)


@router.post("/analysis-events/{event_id}/restore", response_model=AnalysisEvent)
def restore_event(event_id: int, reason: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = AnalysisEventService.get(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Analysis event not found")
    return AnalysisEventService.set_active(db, event, True, reason, user)


@router.get("/analysis-events/{event_id}/revisions", response_model=List[AnalysisEventRevision])
def list_revisions(event_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return AnalysisEventService.revisions(db, event_id)
