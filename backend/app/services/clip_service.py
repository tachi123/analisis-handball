from sqlalchemy.orm import Session
from ..models import Clip
from ..schemas import ClipCreate, ClipUpdate


class ClipService:
    @staticmethod
    def get_by_match(db: Session, match_id: int):
        return (
            db.query(Clip)
            .filter(Clip.match_id == match_id)
            .order_by(Clip.video_start.asc())
            .all()
        )

    @staticmethod
    def create(db: Session, data: ClipCreate):
        obj = Clip(**data.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, clip_id: int, data: ClipUpdate):
        obj = db.query(Clip).filter(Clip.id == clip_id).first()
        if not obj:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, clip_id: int) -> bool:
        obj = db.query(Clip).filter(Clip.id == clip_id).first()
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
