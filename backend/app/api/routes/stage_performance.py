from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import User
from ...services import stage_performance_service as service


router = APIRouter(prefix="/stages", tags=["stage-performance"])


def _rules(win_points: int, draw_points: int, loss_points: int, tiebreak: str) -> service.StandingsRules:
    try:
        return service.StandingsRules(
            win_points=win_points,
            draw_points=draw_points,
            loss_points=loss_points,
            tiebreak_order=tuple(part.strip() for part in tiebreak.split(",") if part.strip()),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _read(call):
    try:
        return call()
    except service.NoConfirmedOfficialDataError as error:
        raise HTTPException(status_code=409, detail="no_confirmed_official_data") from error


@router.get("/{stage_id}/standings")
def get_standings(
    stage_id: int,
    win_points: int = Query(2),
    draw_points: int = Query(1),
    loss_points: int = Query(0),
    tiebreak: str = Query("points,goal_difference,goals_for,team_name"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rules = _rules(win_points, draw_points, loss_points, tiebreak)
    return _read(lambda: service.standings(db, stage_id, rules))


@router.get("/{stage_id}/scorers")
def get_scorers(stage_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return _read(lambda: service.top_scorers(db, stage_id))


@router.get("/{stage_id}/player-averages")
def get_player_averages(stage_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return _read(lambda: service.player_averages(db, stage_id))
