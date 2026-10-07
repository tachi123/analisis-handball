from sqlalchemy import Column, Integer, String, Boolean, Float, Date, ForeignKey, DateTime, JSON, Text, UniqueConstraint, event, text
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from uuid import uuid4
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
    date = Column(Date, nullable=True)
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
    scheduled_match_id = Column(Integer, ForeignKey("scheduled_matches.id"), nullable=True, unique=True)
    canonical_analysis_enabled = Column(Boolean, nullable=False, default=False)
    # `manual` records are intentionally outside the imported fixture graph.
    origin = Column(String, nullable=False, default="legacy", server_default=text("'legacy'"), index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=text("CURRENT_TIMESTAMP"), nullable=False)

    tournament = relationship("Tournament", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    squad = relationship("MatchSquad", back_populates="match", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="match", cascade="all, delete-orphan")
    clips = relationship("Clip", back_populates="match", cascade="all, delete-orphan")
    official_snapshots = relationship("OfficialSnapshot", back_populates="match", cascade="all, delete-orphan")
    analysis_events = relationship("AnalysisEvent", back_populates="match", cascade="all, delete-orphan")
    video_sources = relationship("VideoSource", back_populates="match", cascade="all, delete-orphan")
    analysis_sessions = relationship("AnalysisSession", back_populates="match", cascade="all, delete-orphan")
    report_packages = relationship("ReportPackage", back_populates="match", cascade="all, delete-orphan")
    goalkeeper_shots = relationship("GoalkeeperShot", back_populates="match", cascade="all, delete-orphan")
    canonical_events = relationship("CanonicalEvent", back_populates="match", cascade="all, delete-orphan")
    scheduled_match = relationship("ScheduledMatch", back_populates="analysis_match")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class OfficialSnapshot(Base):
    __tablename__ = "official_snapshots"

    id = Column(String, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    source_filename = Column(String, nullable=False)
    source_content_type = Column(String, nullable=False)
    source_size_bytes = Column(Integer, nullable=False)
    source_sha256 = Column(String, nullable=False)
    source_page_count = Column(Integer, nullable=False)
    source_path = Column(String, nullable=False)
    confirmed_date = Column(Date, nullable=False)
    home_team_name = Column(String, nullable=False)
    away_team_name = Column(String, nullable=False)
    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    batch_run_id = Column(Integer, ForeignKey("official_batch_runs.id"), nullable=True, index=True)
    is_confirmed = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="official_snapshots")
    batch_run = relationship("OfficialBatchRun", back_populates="snapshots")
    players = relationship("OfficialSnapshotPlayer", back_populates="snapshot", cascade="all, delete-orphan")


class OfficialSnapshotPlayer(Base):
    __tablename__ = "official_snapshot_players"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(String, ForeignKey("official_snapshots.id"), nullable=False)
    side = Column(String, nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    name = Column(String, nullable=False)
    jersey_number = Column(Integer, nullable=False)
    official_goals = Column(Integer, nullable=False)
    official_yellow = Column(Integer, nullable=False)
    official_2min = Column(Integer, nullable=False)
    official_red = Column(Integer, nullable=False)
    official_blue = Column(Integer, nullable=False)

    snapshot = relationship("OfficialSnapshot", back_populates="players")


class OfficialBatchRun(Base):
    __tablename__ = "official_batch_runs"

    id = Column(Integer, primary_key=True)
    manifest_sha256 = Column(String(64), nullable=False, index=True)
    derived_sha256 = Column(String(64), nullable=False, index=True)
    mapping_sha256 = Column(String(64), nullable=True)
    status = Column(String, nullable=False)
    report = Column(JSON, nullable=False, default=dict)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    rolled_back_at = Column(DateTime, nullable=True)

    snapshots = relationship("OfficialSnapshot", back_populates="batch_run")


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


class AnalysisCodebookEntry(Base):
    __tablename__ = "analysis_codebook_entries"

    id = Column(Integer, primary_key=True)
    version = Column(String, nullable=False)
    code = Column(String, nullable=False)
    category = Column(String, nullable=False)


class AnalysisEvent(Base):
    __tablename__ = "analysis_events"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    codebook_entry_id = Column(Integer, ForeignKey("analysis_codebook_entries.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period = Column(Integer, nullable=False, default=1)
    regulation_seconds = Column(Float, nullable=True)
    video_timestamp = Column(Float, nullable=True)
    clock_unverified = Column(Boolean, nullable=False, default=False)
    team_action = Column(String, nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    turnover_cause = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    evidence_state = Column(String, nullable=False)
    source = Column(String, nullable=True)
    angle = Column(String, nullable=True)
    note = Column(String, nullable=True)
    included = Column(Boolean, nullable=False, default=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="analysis_events")
    codebook_entry = relationship("AnalysisCodebookEntry")


class AnalysisEventRevision(Base):
    __tablename__ = "analysis_event_revisions"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("analysis_events.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    before_payload = Column(JSON, nullable=True)
    after_payload = Column(JSON, nullable=True)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("AnalysisEvent")


class CanonicalEvent(Base):
    __tablename__ = "canonical_events"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    __table_args__ = (UniqueConstraint("match_id", "sequence", name="uq_canonical_event_sequence"),)

    match = relationship("Match", back_populates="canonical_events")
    revisions = relationship("CanonicalEventRevision", back_populates="event", cascade="all, delete-orphan")


class CanonicalEventRevision(Base):
    __tablename__ = "canonical_event_revisions"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("canonical_events.id"), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payload = Column(JSON, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    __table_args__ = (UniqueConstraint("event_id", "revision", name="uq_canonical_event_revision"),)

    event = relationship("CanonicalEvent", back_populates="revisions")
    evidence = relationship("CanonicalEvidence", back_populates="revision", cascade="all, delete-orphan")
    projections = relationship("CanonicalProjection", back_populates="revision", cascade="all, delete-orphan")


class CanonicalEvidence(Base):
    __tablename__ = "canonical_evidence"

    id = Column(Integer, primary_key=True)
    revision_id = Column(Integer, ForeignKey("canonical_event_revisions.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    scheduled_match_id = Column(Integer, ForeignKey("scheduled_matches.id"), nullable=True)
    official_snapshot_id = Column(String, ForeignKey("official_snapshots.id"), nullable=True)
    video_source_id = Column(Integer, ForeignKey("video_sources.id"), nullable=True)
    video_anchor_seconds = Column(Float, nullable=True)
    report_package_id = Column(Integer, ForeignKey("report_packages.id"), nullable=True)
    uncertainty = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    revision = relationship("CanonicalEventRevision", back_populates="evidence")
    scheduled_match = relationship("ScheduledMatch")
    official_snapshot = relationship("OfficialSnapshot")
    video_source = relationship("VideoSource")
    report_package = relationship("ReportPackage")


class CanonicalProjection(Base):
    __tablename__ = "canonical_projections"

    id = Column(Integer, primary_key=True)
    revision_id = Column(Integer, ForeignKey("canonical_event_revisions.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    revision = relationship("CanonicalEventRevision", back_populates="projections")


class VideoSource(Base):
    __tablename__ = "video_sources"
    __table_args__ = (
        UniqueConstraint("match_id", "provider", "provider_video_id", name="uq_video_source_match_provider_video"),
    )

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    original_url = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    provider_video_id = Column(String, nullable=False)
    availability_state = Column(String, nullable=False, default="unknown")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="video_sources")


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_source_id = Column(Integer, ForeignKey("video_sources.id"), nullable=True)
    mode = Column(String, nullable=False, default="live")
    profile = Column(String, nullable=False, default="complete")
    video_position_seconds = Column(Float, nullable=True)
    clock_start_video_seconds = Column(Float, nullable=True)
    angle = Column(String, nullable=True)
    filters = Column(JSON, nullable=False, default=dict)
    draft = Column(JSON, nullable=False, default=dict)
    queue = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="analysis_sessions")
    video_source = relationship("VideoSource")
    anchors = relationship("TimeAnchor", back_populates="session", cascade="all, delete-orphan")
    time_segments = relationship("TimeSegment", back_populates="session", cascade="all, delete-orphan")


class TimeAnchor(Base):
    __tablename__ = "time_anchors"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period = Column(Integer, nullable=False)
    video_seconds = Column(Float, nullable=False)
    regulation_seconds = Column(Float, nullable=False)
    uncertainty_seconds = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("AnalysisSession", back_populates="anchors")


class TimeSegment(Base):
    __tablename__ = "time_segments"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("analysis_sessions.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period = Column(Integer, nullable=False)
    video_start_seconds = Column(Float, nullable=False)
    video_end_seconds = Column(Float, nullable=False)
    regulation_start_seconds = Column(Float, nullable=True)
    regulation_end_seconds = Column(Float, nullable=True)
    uncertainty_seconds = Column(Float, nullable=False, default=0)
    coverage = Column(String, nullable=False)
    clock_unverified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("AnalysisSession", back_populates="time_segments")


class ReportPackage(Base):
    __tablename__ = "report_packages"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_version = Column(Integer, nullable=False, default=1)
    schema_version = Column(String, nullable=False, default="public-report-v1")
    coaching_question = Column(String, nullable=False)
    pattern_statement = Column(String, nullable=False)
    action_kind = Column(String, nullable=False)
    action_text = Column(String, nullable=False)
    uncertainty_disclosure = Column(String, nullable=False)
    metrics = Column(JSON, nullable=False, default=dict)
    reconciliation = Column(JSON, nullable=False, default=list)
    source_label = Column(String, nullable=True)
    source_status = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    match = relationship("Match", back_populates="report_packages")
    evidence = relationship("ReportPackageEvidence", back_populates="package", cascade="all, delete-orphan")
    publications = relationship("ReportPublication", back_populates="package", cascade="all, delete-orphan")
    recovery_artifacts = relationship("RecoveryArtifact", back_populates="package", cascade="all, delete-orphan")


class ReportPackageEvidence(Base):
    __tablename__ = "report_package_evidence"

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey("report_packages.id"), nullable=False)
    analysis_event_id = Column(Integer, ForeignKey("analysis_events.id"), nullable=True)
    reference = Column(String, nullable=False)
    period = Column(Integer, nullable=False)
    regulation_seconds = Column(Float, nullable=True)
    clock_unverified = Column(Boolean, nullable=False, default=False)
    public_observation = Column(String, nullable=True)
    private_note = Column(String, nullable=True)
    public_media_url = Column(String, nullable=True)
    public_approved = Column(Boolean, nullable=False, default=False)
    media_public_approved = Column(Boolean, nullable=False, default=False)

    package = relationship("ReportPackage", back_populates="evidence")


class RecoveryArtifact(Base):
    __tablename__ = "recovery_artifacts"
    __table_args__ = (UniqueConstraint("package_id", "artifact_type", name="uq_recovery_artifact_package_type"),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey("report_packages.id"), nullable=False)
    artifact_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    attested_at = Column(DateTime, nullable=True)
    attested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    package = relationship("ReportPackage", back_populates="recovery_artifacts")


class ReportPublication(Base):
    __tablename__ = "report_publications"
    __table_args__ = (UniqueConstraint("package_id", "report_version", name="uq_report_publication_version"),)

    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey("report_packages.id"), nullable=False)
    report_version = Column(Integer, nullable=False)
    schema_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    published_at = Column(DateTime, nullable=True)

    package = relationship("ReportPackage", back_populates="publications")


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


# ─── Competition Layer (Parallel Domain) ──────────────────────────────────────────────


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True)
    year = Column(Integer, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    stages = relationship("TournamentStage", back_populates="season", cascade="all, delete-orphan")


class TournamentStage(Base):
    __tablename__ = "tournament_stages"

    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    division = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("season_id", "name", name="uq_stage_season_name"),)
    season = relationship("Season", back_populates="stages")
    registrations = relationship("TeamRegistration", back_populates="stage")
    rounds = relationship("Round", back_populates="stage")
    competition_teams = relationship("CompetitionTeam", back_populates="stage")
    scheduled_matches = relationship("ScheduledMatch", back_populates="stage")
    fixture_imports = relationship("FixtureImport", back_populates="stage")


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    short_name = Column(String, nullable=True)
    competition_teams = relationship("CompetitionTeam", back_populates="club")


class CompetitionTeam(Base):
    __tablename__ = "competition_teams"

    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False, index=True)
    stage_id = Column(Integer, ForeignKey("tournament_stages.id"), nullable=False, index=True)
    suffix = Column(String(2), nullable=True)
    variant_key = Column(String(2), nullable=False)
    external_code = Column(String(64), nullable=True, unique=True, index=True)
    __table_args__ = (UniqueConstraint("club_id", "stage_id", "variant_key", name="uq_comp_team_variant_identity"),)
    club = relationship("Club", back_populates="competition_teams")
    stage = relationship("TournamentStage", back_populates="competition_teams")
    registrations = relationship("TeamRegistration", back_populates="competition_team")

    @property
    def display_name(self) -> str:
        return f"{self.club.name} {self.suffix}" if self.suffix else self.club.name

    @property
    def variant(self) -> str | None:
        return self.suffix


class TeamRegistration(Base):
    __tablename__ = "team_registrations"

    id = Column(Integer, primary_key=True)
    competition_team_id = Column(Integer, ForeignKey("competition_teams.id"), nullable=False, index=True)
    stage_id = Column(Integer, ForeignKey("tournament_stages.id"), nullable=False, index=True)
    group = Column(String, nullable=True)
    seed_order = Column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint("competition_team_id", "stage_id", name="uq_registration_team_stage"),)
    competition_team = relationship("CompetitionTeam", back_populates="registrations")
    stage = relationship("TournamentStage", back_populates="registrations")
    home_matches = relationship("ScheduledMatch", foreign_keys="ScheduledMatch.home_registration_id", back_populates="home_registration")
    away_matches = relationship("ScheduledMatch", foreign_keys="ScheduledMatch.away_registration_id", back_populates="away_registration")
    roster = relationship("StageRoster", back_populates="registration", cascade="all, delete-orphan")


class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True)
    stage_id = Column(Integer, ForeignKey("tournament_stages.id"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    __table_args__ = (UniqueConstraint("stage_id", "round_number", name="uq_round_stage_number"),)
    stage = relationship("TournamentStage", back_populates="rounds")
    matches = relationship("ScheduledMatch", back_populates="round")


class ScheduledMatch(Base):
    __tablename__ = "scheduled_matches"

    id = Column(Integer, primary_key=True)
    stage_id = Column(Integer, ForeignKey("tournament_stages.id"), nullable=False, index=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False, index=True)
    home_registration_id = Column(Integer, ForeignKey("team_registrations.id"), nullable=False, index=True)
    away_registration_id = Column(Integer, ForeignKey("team_registrations.id"), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=True)
    venue = Column(String, nullable=True)
    court = Column(String, nullable=True)
    match_time = Column(String, nullable=True)
    match_number_label = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="scheduled")
    fixture_key = Column(String, nullable=False, unique=True, index=True, default=lambda: f"manual:{uuid4().hex}")
    source_home_score = Column(Integer, nullable=True)
    source_away_score = Column(Integer, nullable=True)
    result_status = Column(String, nullable=False, default="unreported")
    __table_args__ = (UniqueConstraint("round_id", "match_number_label", name="uq_match_round_label"),)
    stage = relationship("TournamentStage", back_populates="scheduled_matches")
    round = relationship("Round", back_populates="matches")
    home_registration = relationship("TeamRegistration", foreign_keys=[home_registration_id], back_populates="home_matches")
    away_registration = relationship("TeamRegistration", foreign_keys=[away_registration_id], back_populates="away_matches")
    fixture_import_entries = relationship("FixtureImportEntry", back_populates="scheduled_match")
    analysis_match = relationship("Match", back_populates="scheduled_match", uselist=False)

    @validates("fixture_key")
    def prevent_fixture_key_change(self, _, value):
        if self.id is not None and self.fixture_key is not None and value != self.fixture_key:
            raise ValueError("fixture_key is immutable")
        return value


class FixtureImport(Base):
    __tablename__ = "fixture_imports"

    id = Column(Integer, primary_key=True)
    stage_id = Column(Integer, ForeignKey("tournament_stages.id"), nullable=False, index=True)
    source_label = Column(String, nullable=False)
    captured_at = Column(DateTime, nullable=False)
    source_sha256 = Column(String(64), nullable=False, unique=True, index=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    stage = relationship("TournamentStage", back_populates="fixture_imports")
    entries = relationship("FixtureImportEntry", back_populates="fixture_import", cascade="all, delete-orphan")


class FixtureImportEntry(Base):
    __tablename__ = "fixture_import_entries"
    __table_args__ = (UniqueConstraint("fixture_import_id", "entry_key", name="uq_fixture_import_entry_key"),)

    id = Column(Integer, primary_key=True)
    fixture_import_id = Column(Integer, ForeignKey("fixture_imports.id"), nullable=False, index=True)
    entry_key = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    raw_entry = Column(JSON, nullable=False)
    scheduled_match_id = Column(Integer, ForeignKey("scheduled_matches.id"), nullable=True, index=True)

    fixture_import = relationship("FixtureImport", back_populates="entries")
    scheduled_match = relationship("ScheduledMatch", back_populates="fixture_import_entries")


@event.listens_for(CompetitionTeam, "before_insert")
def set_competition_team_variant_key(_, __, target):
    if target.variant_key is None:
        target.variant_key = target.suffix or ""


class StageRoster(Base):
    __tablename__ = "stage_rosters"

    id = Column(Integer, primary_key=True)
    registration_id = Column(Integer, ForeignKey("team_registrations.id"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    jersey_number = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("registration_id", "jersey_number", name="uq_roster_jersey"),)
    registration = relationship("TeamRegistration", back_populates="roster")
    player = relationship("Player")
