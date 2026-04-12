from sqlalchemy.orm import Session
from ..models import Tournament
from ..schemas import TournamentCreate, TournamentUpdate


class TournamentService:
    @staticmethod
    def get_all(db: Session):
        return db.query(Tournament).order_by(Tournament.year.desc()).all()

    @staticmethod
    def get_by_id(db: Session, tournament_id: int):
        return db.query(Tournament).filter(Tournament.id == tournament_id).first()

    @staticmethod
    def create(db: Session, data: TournamentCreate):
        obj = Tournament(name=data.name, category=data.category, year=data.year)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, tournament_id: int, data: TournamentUpdate):
        obj = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, tournament_id: int) -> bool:
        obj = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
