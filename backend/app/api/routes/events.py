from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ...deps import get_current_user
from ...models import User
from ...schemas import Event, EventCreate
from ...services.event_service import EventService

router = APIRouter(prefix="/matches", tags=["events"])


@router.get("/{match_id}/events", response_model=List[Event])
def list_events(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return EventService.get_by_match(db, match_id)


@router.post("/{match_id}/events", response_model=Event, status_code=201)
def create_event(match_id: int, data: EventCreate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    if data.match_id != match_id:
        raise HTTPException(status_code=400, detail="match_id no coincide con la URL")
    return EventService.create(db, data)


@router.delete("/{match_id}/events/last", response_model=Event)
def delete_last_event(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    last = EventService.get_last_by_match(db, match_id)
    if not last:
        raise HTTPException(status_code=404, detail="No hay eventos para este partido")
    EventService.delete(db, last.id)
    return last


@router.delete("/{match_id}/events/{event_id}", status_code=204)
def delete_event(match_id: int, event_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    if not EventService.delete(db, event_id):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
