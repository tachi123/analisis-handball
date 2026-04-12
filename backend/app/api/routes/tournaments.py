from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...schemas import Tournament, TournamentCreate, TournamentUpdate
from ...services.tournament_service import TournamentService

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("/", response_model=List[Tournament])
def list_tournaments(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return TournamentService.get_all(db)


@router.get("/{tournament_id}", response_model=Tournament)
def get_tournament(tournament_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    obj = TournamentService.get_by_id(db, tournament_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return obj


@router.post("/", response_model=Tournament, status_code=201)
def create_tournament(data: TournamentCreate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    return TournamentService.create(db, data)


@router.patch("/{tournament_id}", response_model=Tournament)
def update_tournament(tournament_id: int, data: TournamentUpdate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    obj = TournamentService.update(db, tournament_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
    return obj


@router.delete("/{tournament_id}", status_code=204)
def delete_tournament(tournament_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if not TournamentService.delete(db, tournament_id):
        raise HTTPException(status_code=404, detail="Torneo no encontrado")
