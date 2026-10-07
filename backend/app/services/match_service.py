from sqlalchemy.orm import Session, joinedload
from ..models import Match, MatchSquad, Team, Tournament, User
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
    def create(db: Session, data: MatchCreate, user: User):
        if db.get(Team, data.home_team_id) is None or db.get(Team, data.away_team_id) is None:
            raise ValueError("El equipo seleccionado no existe")
        if data.tournament_id is not None and db.get(Tournament, data.tournament_id) is None:
            raise ValueError("El torneo seleccionado no existe")
        duplicate = db.query(Match).filter(
            Match.origin == "manual",
            Match.home_team_id == data.home_team_id,
            Match.away_team_id == data.away_team_id,
            Match.date == data.date,
        ).first()
        if duplicate:
            raise ValueError("Ya existe un partido manual con los mismos equipos y fecha")
        obj = Match(**data.model_dump(), origin="manual", created_by_user_id=user.id)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return MatchService.get_by_id(db, obj.id)

    @staticmethod
    def update(db: Session, match_id: int, data: MatchUpdate, user: User):
        obj = db.query(Match).filter(Match.id == match_id).first()
        if not obj:
            return None
        if obj.origin != "manual":
            raise ValueError("Solo los partidos manuales se pueden actualizar por esta vía")
        if user.role not in {"admin", "superadmin"} and obj.created_by_user_id != user.id:
            raise PermissionError("Solo puede actualizar sus propios partidos manuales")
        values = data.model_dump(exclude_unset=True)
        home_team_id = values.get("home_team_id", obj.home_team_id)
        away_team_id = values.get("away_team_id", obj.away_team_id)
        if home_team_id is not None and home_team_id == away_team_id:
            raise ValueError("Los equipos local y visitante deben ser distintos")
        for field, value in values.items():
            setattr(obj, field, value)
        db.commit()
        return MatchService.get_by_id(db, match_id)

    @staticmethod
    def require_manual_owner(db: Session, match_id: int, user: User) -> Match:
        match = db.get(Match, match_id)
        if match is None:
            raise ValueError("Partido no encontrado")
        if match.origin != "manual":
            raise ValueError("Esta operación solo está disponible para partidos manuales")
        if user.role not in {"admin", "superadmin"} and match.created_by_user_id != user.id:
            raise PermissionError("Solo puede preparar sus propios partidos manuales")
        return match

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
