from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import User

from ...services.statistics_service import player_statistics, club_statistics


router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/players")
def get_player_statistics(
    stage_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Return per-player aggregated statistics for the given stage.

    Only ``OfficialSnapshot.is_confirmed == True`` snapshots are counted.
    Rows are sorted by goals descending, then appearances descending.
    """
    result = player_statistics(db, stage_id)
    return result


@router.get("/clubs")
def get_club_statistics(
    stage_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Return per-club aggregated statistics for the given stage.

    Only ``OfficialSnapshot.is_confirmed == True`` snapshots are counted.
    Rows are sorted by goals descending.
    """
    result = club_statistics(db, stage_id)
    return result