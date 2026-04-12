from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...schemas import Team, TeamCreate, TeamUpdate
from ...services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/", response_model=List[Team])
def list_teams(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return TeamService.get_all(db)


@router.get("/{team_id}", response_model=Team)
def get_team(team_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    obj = TeamService.get_by_id(db, team_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


@router.post("/", response_model=Team, status_code=201)
def create_team(data: TeamCreate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    return TeamService.create(db, data)


@router.patch("/{team_id}", response_model=Team)
def update_team(team_id: int, data: TeamUpdate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    obj = TeamService.update(db, team_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if not TeamService.delete(db, team_id):
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
