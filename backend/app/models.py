from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="analyst")  # superadmin | admin | analyst
    club_id = Column(Integer, nullable=True)  # FK to clubs table — Fase 3
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    year = Column(Integer)

    matches = relationship("Match", back_populates="tournament")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    club_name = Column(String, nullable=True)
    category = Column(String, nullable=True)

    players = relationship("Player", back_populates="team")
    home_matches = relationship("Match", foreign_keys="[Match.home_team_id]", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="[Match.away_team_id]", back_populates="away_team")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    default_jersey_number = Column(Integer, nullable=True)
    global_position = Column(String, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team = relationship("Team", back_populates="players")
    matches_played = relationship("MatchSquad", back_populates="player")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=True)
    date = Column(Date)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    youtube_link = Column(String, nullable=True)
    main_team_focus = Column(String, default="SAPA")
    venue = Column(String, nullable=True)
    court = Column(String, nullable=True)
    match_time = Column(String, nullable=True)
    category_label = Column(String, nullable=True)
    match_number_label = Column(String, nullable=True)
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)
    pdf_file_path = Column(String, nullable=True)
    goalkeeper_shots = relationship("GoalkeeperShot", back_populates="match", cascade="all, delete-orphan")

    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    squad = relationship("MatchSquad", back_populates="match", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="match", cascade="all, delete-orphan")
    clips = relationship("Clip", back_populates="match", cascade="all, delete-orphan")


class MatchSquad(Base):
    __tablename__ = "match_squad"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    jersey_number = Column(Integer, nullable=False)
    is_goalkeeper = Column(Boolean, default=False)
    official_goals = Column(Integer, default=0)
    official_yellow = Column(Integer, default=0)
    official_2min = Column(Integer, default=0)
    official_red = Column(Integer, default=0)
    official_blue = Column(Integer, default=0)

    match = relationship("Match", back_populates="squad")
    player = relationship("Player", back_populates="matches_played")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    game_timestamp = Column(Float)
    period = Column(Integer, nullable=True)
    team_action = Column(String)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    action_type = Column(String)
    result = Column(String, nullable=True)
    shot_zone = Column(String, nullable=True)
    loss_detail = Column(String, nullable=True)
    attack_phase = Column(String, nullable=True)
    assist_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    goalkeeper_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    sub_in_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    sub_out_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    transition_type = Column(String, nullable=True)
    transition_result = Column(String, nullable=True)
    sanction_type = Column(String, nullable=True)
    sanction_target = Column(String, nullable=True)

    match = relationship("Match", back_populates="events")
    player = relationship("Player", foreign_keys=[player_id])
    assist_player = relationship("Player", foreign_keys=[assist_player_id])
    goalkeeper = relationship("Player", foreign_keys=[goalkeeper_id])
    sub_in_player = relationship("Player", foreign_keys=[sub_in_player_id])
    sub_out_player = relationship("Player", foreign_keys=[sub_out_player_id])


class Clip(Base):
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    video_start = Column(Float)
    video_end = Column(Float)
    title = Column(String)
    player_tags = Column(String, nullable=True)

    match = relationship("Match", back_populates="clips")

class GoalkeeperShot(Base):
    __tablename__ = "goalkeeper_shots"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    shooter_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    shooter_label = Column(String(16), nullable=True)
    period = Column(Integer, nullable=True)  # 1 or 2
    video_timestamp = Column(Float, nullable=True)  # reserved for future video sync
    origin_zone = Column(String(24), nullable=True)
    target_zone = Column(String(16), nullable=True)
    shot_type = Column(String(8), nullable=True)
    outcome = Column(String(12), nullable=True)
    note = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="goalkeeper_shots")
    shooter_player = relationship("Player")
