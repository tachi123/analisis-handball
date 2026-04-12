from sqlalchemy.orm import Session

from ..models import User
from ..security import get_password_hash, verify_password


class AuthService:
    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, email: str, password: str, full_name: str, role: str = "analyst") -> User:
        user = User(
            email=email.lower().strip(),
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        user = AuthService.get_by_email(db, email.lower().strip())
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def change_password(db: Session, user: User, new_password: str) -> User:
        user.hashed_password = get_password_hash(new_password)
        user.must_change_password = False
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_all_users(db: Session) -> list[User]:
        return db.query(User).order_by(User.id).all()
