from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...schemas import Clip, ClipCreate, ClipUpdate
from ...services.clip_service import ClipService

router = APIRouter(prefix="/matches", tags=["clips"])


@router.get("/{match_id}/clips", response_model=List[Clip])
def list_clips(match_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return ClipService.get_by_match(db, match_id)


@router.post("/{match_id}/clips", response_model=Clip, status_code=201)
def create_clip(match_id: int, data: ClipCreate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if data.match_id != match_id:
        raise HTTPException(status_code=400, detail="match_id no coincide con la URL")
    return ClipService.create(db, data)


@router.patch("/{match_id}/clips/{clip_id}", response_model=Clip)
def update_clip(match_id: int, clip_id: int, data: ClipUpdate, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    obj = ClipService.update(db, clip_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Clip no encontrado")
    return obj


@router.delete("/{match_id}/clips/{clip_id}", status_code=204)
def delete_clip(match_id: int, clip_id: int, db: Session = Depends(get_db), _user: User = Depends(require_role("superadmin", "admin"))):
    if not ClipService.delete(db, clip_id):
        raise HTTPException(status_code=404, detail="Clip no encontrado")
