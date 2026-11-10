from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import User
from ...services.standings_service import get_point_rules, compute_standings, StandingsPointRules


router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("")
def get_standings(
    stage_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return tournament standings for the given stage_id.

    The points rule is loaded from the versioned config (not hardcoded).
    Only matches with a recorded result (both scores present) are counted.
    Suspended fixtures use the suspended rule: winner 3 pts, loser 0 pts.
    """
    rules = get_point_rules(db, stage_id)
    # We don't need the rules for the compute_standings call since it loads internally,
    # but we validate they're loadable.
    result = compute_standings(db, stage_id)
    return result