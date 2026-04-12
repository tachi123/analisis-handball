from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...schemas import Player, PlayerCreate, PlayerUpdate
from ...services.player_service import PlayerService

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/", response_model=List[Player])
def list_players(team_id: Optional[int] = Query(None), db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    if team_id is not None:
        return PlayerService.get_by_team(db, team_id)
    return PlayerService.get_all(db)


@router.get("/{player_id}", response_model=Player)
def get_player(player_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    obj = PlayerService.get_by_id(db, player_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return obj


@router.post("/", response_model=Player, status_code=201)
def create_player(data: PlayerCreate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    return PlayerService.create(db, data)


@router.patch("/{player_id}", response_model=Player)
def update_player(player_id: int, data: PlayerUpdate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    obj = PlayerService.update(db, player_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
    return obj


@router.delete("/{player_id}", status_code=204)
def delete_player(player_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if not PlayerService.delete(db, player_id):
        raise HTTPException(status_code=404, detail="Jugador no encontrado")
