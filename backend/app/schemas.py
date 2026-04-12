from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date


# ─── Tournament ────────────────────────────────────────────────────────────────

class TournamentBase(BaseModel):
    name: str
    category: str
    year: int


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    year: Optional[int] = None


class Tournament(TournamentBase):
    id: int

    class Config:
        from_attributes = True


# ─── Team ──────────────────────────────────────────────────────────────────────

class TeamBase(BaseModel):
    name: str
    club_name: Optional[str] = None
    category: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    club_name: Optional[str] = None
    category: Optional[str] = None


class Team(TeamBase):
    id: int

    class Config:
        from_attributes = True


# ─── Player ────────────────────────────────────────────────────────────────────

class PlayerBase(BaseModel):
    name: str
    default_jersey_number: Optional[int] = None
    global_position: Optional[str] = None
    team_id: Optional[int] = None


class PlayerCreate(PlayerBase):
    pass


class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    default_jersey_number: Optional[int] = None
    global_position: Optional[str] = None
    team_id: Optional[int] = None


class Player(PlayerBase):
    id: int
    team: Optional[Team] = None

    class Config:
        from_attributes = True


# ─── MatchSquad ────────────────────────────────────────────────────────────────

class MatchSquadBase(BaseModel):
    match_id: int
    player_id: int
    jersey_number: int
    is_goalkeeper: bool = False
    official_goals: int = 0
    official_yellow: int = 0
    official_2min: int = 0
    official_red: int = 0
    official_blue: int = 0


class MatchSquadCreate(MatchSquadBase):
    pass


class MatchSquad(MatchSquadBase):
    id: int
    player: Optional[Player] = None

    class Config:
        from_attributes = True


# ─── Match ─────────────────────────────────────────────────────────────────────

class MatchBase(BaseModel):
    tournament_id: Optional[int] = None
    date: date
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    youtube_link: Optional[str] = None
    main_team_focus: str = "SAPA"
    venue: Optional[str] = None
    court: Optional[str] = None
    match_time: Optional[str] = None
    category_label: Optional[str] = None
    match_number_label: Optional[str] = None
    home_score: int = 0
    away_score: int = 0
    pdf_file_path: Optional[str] = None


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    tournament_id: Optional[int] = None
    date: Optional[date] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    youtube_link: Optional[str] = None
    main_team_focus: Optional[str] = None
    venue: Optional[str] = None
    court: Optional[str] = None
    match_time: Optional[str] = None
    category_label: Optional[str] = None
    match_number_label: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    pdf_file_path: Optional[str] = None


class Match(MatchBase):
    id: int
    tournament: Optional[Tournament] = None
    home_team: Optional[Team] = None
    away_team: Optional[Team] = None
    squad: List[MatchSquad] = []

    class Config:
        from_attributes = True


# ─── Event ─────────────────────────────────────────────────────────────────────

class EventBase(BaseModel):
    game_timestamp: float
    period: Optional[int] = None
    team_action: str
    player_id: Optional[int] = None
    action_type: str
    result: Optional[str] = None
    shot_zone: Optional[str] = None
    loss_detail: Optional[str] = None
    attack_phase: Optional[str] = None
    assist_player_id: Optional[int] = None
    goalkeeper_id: Optional[int] = None
    sub_in_player_id: Optional[int] = None
    sub_out_player_id: Optional[int] = None
    transition_type: Optional[str] = None
    transition_result: Optional[str] = None
    sanction_type: Optional[str] = None
    sanction_target: Optional[str] = None


class EventCreate(EventBase):
    match_id: int


class Event(EventBase):
    id: int
    match_id: int
    player: Optional[Player] = None
    assist_player: Optional[Player] = None
    goalkeeper: Optional[Player] = None
    sub_in_player: Optional[Player] = None
    sub_out_player: Optional[Player] = None

    class Config:
        from_attributes = True


# ─── Clip ──────────────────────────────────────────────────────────────────────

class ClipBase(BaseModel):
    video_start: float
    video_end: float
    title: str
    player_tags: Optional[str] = None


class ClipCreate(ClipBase):
    match_id: int


class ClipUpdate(BaseModel):
    video_start: Optional[float] = None
    video_end: Optional[float] = None
    title: Optional[str] = None
    player_tags: Optional[str] = None


class Clip(ClipBase):
    id: int
    match_id: int

    class Config:
        from_attributes = True


# ─── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "analyst"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("superadmin", "admin", "analyst"):
            raise ValueError("role must be superadmin, admin, or analyst")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    club_id: int | None = None
    is_active: bool
    must_change_password: bool

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v
