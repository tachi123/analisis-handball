from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import GoalkeeperShot as GoalkeeperShotModel, Match, User
from ...schemas import GoalkeeperShot, GoalkeeperShotCreate
from ...services.canonical_analysis_service import LegacyWriteBlockedError, ensure_legacy_writes_allowed

router = APIRouter(prefix="/matches", tags=["goalkeeper-shots"])


def _get_shot(match_id: int, shot_id: int, db: Session) -> GoalkeeperShotModel:
    shot = db.query(GoalkeeperShotModel).filter(
        GoalkeeperShotModel.id == shot_id,
        GoalkeeperShotModel.match_id == match_id,
    ).first()
    if shot is None:
        raise HTTPException(status_code=404, detail="Tiro no encontrado")
    return shot


@router.get("/{match_id}/goalkeeper-shots", response_model=List[GoalkeeperShot])
def list_goalkeeper_shots(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return db.query(GoalkeeperShotModel).filter(GoalkeeperShotModel.match_id == match_id).order_by(GoalkeeperShotModel.id.asc()).all()


@router.post("/{match_id}/goalkeeper-shots", response_model=GoalkeeperShot, status_code=201)
def create_goalkeeper_shot(match_id: int, data: GoalkeeperShotCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if db.query(Match).filter(Match.id == match_id).first() is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    try:
        ensure_legacy_writes_allowed(db, match_id)
    except LegacyWriteBlockedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    shot = GoalkeeperShotModel(match_id=match_id, created_by_user_id=user.id, **data.model_dump())
    db.add(shot)
    db.commit()
    db.refresh(shot)
    return shot


@router.delete("/{match_id}/goalkeeper-shots/{shot_id}", status_code=204)
def delete_goalkeeper_shot(match_id: int, shot_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    shot = _get_shot(match_id, shot_id, db)
    try:
        ensure_legacy_writes_allowed(db, match_id)
    except LegacyWriteBlockedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    db.delete(shot)
    db.commit()
