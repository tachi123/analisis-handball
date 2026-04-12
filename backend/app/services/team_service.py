from sqlalchemy.orm import Session
from ..models import Team
from ..schemas import TeamCreate, TeamUpdate


class TeamService:
    @staticmethod
    def get_all(db: Session):
        return db.query(Team).order_by(Team.name).all()

    @staticmethod
    def get_by_id(db: Session, team_id: int):
        return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def create(db: Session, data: TeamCreate):
        obj = Team(name=data.name, club_name=data.club_name, category=data.category)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, team_id: int, data: TeamUpdate):
        obj = db.query(Team).filter(Team.id == team_id).first()
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, team_id: int) -> bool:
        obj = db.query(Team).filter(Team.id == team_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
