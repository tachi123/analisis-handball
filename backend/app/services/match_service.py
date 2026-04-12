from sqlalchemy.orm import Session, joinedload
from ..models import Match, MatchSquad
from ..schemas import MatchCreate, MatchUpdate, MatchSquadCreate


class MatchService:
    @staticmethod
    def get_all(db: Session):
        return (
            db.query(Match)
            .options(
                joinedload(Match.tournament),
                joinedload(Match.home_team),
                joinedload(Match.away_team),
            )
            .order_by(Match.date.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, match_id: int):
        return (
            db.query(Match)
            .options(
                joinedload(Match.tournament),
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.squad).joinedload(MatchSquad.player),
            )
            .filter(Match.id == match_id)
            .first()
        )

    @staticmethod
    def create(db: Session, data: MatchCreate):
        obj = Match(**data.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return MatchService.get_by_id(db, obj.id)

    @staticmethod
    def update(db: Session, match_id: int, data: MatchUpdate):
        obj = db.query(Match).filter(Match.id == match_id).first()
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        return MatchService.get_by_id(db, match_id)

    @staticmethod
    def delete(db: Session, match_id: int) -> bool:
        obj = db.query(Match).filter(Match.id == match_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def upsert_squad_player(db: Session, data: MatchSquadCreate):
        existing = (
            db.query(MatchSquad)
            .filter(
                MatchSquad.match_id == data.match_id,
                MatchSquad.player_id == data.player_id,
            )
            .first()
        )
        if existing:
            for field, value in data.model_dump(exclude={"match_id", "player_id"}).items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        obj = MatchSquad(**data.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def remove_squad_player(db: Session, match_id: int, player_id: int) -> bool:
        obj = (
            db.query(MatchSquad)
            .filter(MatchSquad.match_id == match_id, MatchSquad.player_id == player_id)
            .first()
        )
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True

    @staticmethod
    def get_squad(db: Session, match_id: int):
        return (
            db.query(MatchSquad)
            .options(joinedload(MatchSquad.player))
            .filter(MatchSquad.match_id == match_id)
            .all()
        )
