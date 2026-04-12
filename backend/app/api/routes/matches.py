from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...schemas import Match, MatchCreate, MatchUpdate, MatchSquad, MatchSquadCreate
from ...services.match_service import MatchService

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/", response_model=List[Match])
def list_matches(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return MatchService.get_all(db)


@router.get("/{match_id}", response_model=Match)
def get_match(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    obj = MatchService.get_by_id(db, match_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return obj


@router.post("/", response_model=Match, status_code=201)
def create_match(data: MatchCreate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    return MatchService.create(db, data)


@router.patch("/{match_id}", response_model=Match)
def update_match(match_id: int, data: MatchUpdate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    obj = MatchService.update(db, match_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return obj


@router.delete("/{match_id}", status_code=204)
def delete_match(match_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if not MatchService.delete(db, match_id):
        raise HTTPException(status_code=404, detail="Partido no encontrado")


# Squad ────────────────────────────────────────────────────────────────────────

@router.get("/{match_id}/squad", response_model=List[MatchSquad])
def get_squad(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return MatchService.get_squad(db, match_id)


@router.put("/{match_id}/squad", response_model=MatchSquad)
def upsert_squad_player(match_id: int, data: MatchSquadCreate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if data.match_id != match_id:
        raise HTTPException(status_code=400, detail="match_id no coincide con la URL")
    return MatchService.upsert_squad_player(db, data)


@router.delete("/{match_id}/squad/{player_id}", status_code=204)
def remove_squad_player(match_id: int, player_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if not MatchService.remove_squad_player(db, match_id, player_id):
        raise HTTPException(status_code=404, detail="Jugador no encontrado en la convocatoria")
