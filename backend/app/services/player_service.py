from sqlalchemy.orm import Session
from ..models import Player
from ..schemas import PlayerCreate, PlayerUpdate


class PlayerService:
    @staticmethod
    def get_all(db: Session):
        return db.query(Player).order_by(Player.name).all()

    @staticmethod
    def get_by_id(db: Session, player_id: int):
        return db.query(Player).filter(Player.id == player_id).first()

    @staticmethod
    def get_by_team(db: Session, team_id: int):
        return db.query(Player).filter(Player.team_id == team_id).order_by(Player.name).all()

    @staticmethod
    def create(db: Session, data: PlayerCreate):
        obj = Player(
            name=data.name,
            default_jersey_number=data.default_jersey_number,
            global_position=data.global_position,
            team_id=data.team_id,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, player_id: int, data: PlayerUpdate):
        obj = db.query(Player).filter(Player.id == player_id).first()
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, player_id: int) -> bool:
        obj = db.query(Player).filter(Player.id == player_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
