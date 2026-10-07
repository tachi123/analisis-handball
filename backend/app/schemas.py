from pydantic import AliasChoices, AliasPath, BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal, Optional, List
from datetime import date as Date, datetime


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
    date: Optional[Date] = None
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
    canonical_analysis_enabled: bool = False


class MatchCreate(MatchBase):
    @model_validator(mode="after")
    def validate_teams(self):
        if self.home_team_id is None or self.away_team_id is None:
            raise ValueError("Debe seleccionar equipo local y visitante")
        if self.home_team_id == self.away_team_id:
            raise ValueError("Los equipos local y visitante deben ser distintos")
        return self


class MatchUpdate(BaseModel):
    tournament_id: Optional[int] = None
    date: Optional[Date] = None
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

    @model_validator(mode="after")
    def validate_teams(self):
        if self.home_team_id is not None and self.home_team_id == self.away_team_id:
            raise ValueError("Los equipos local y visitante deben ser distintos")
        return self


class Match(MatchBase):
    id: int
    tournament: Optional[Tournament] = None
    home_team: Optional[Team] = None
    away_team: Optional[Team] = None
    squad: List[MatchSquad] = []
    origin: Literal["manual", "fixture", "legacy"] = "legacy"
    created_by_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class OfficialSheetPlayer(BaseModel):
    player_id: Optional[int] = None
    name: str
    jersey_number: int
    official_goals: int
    official_yellow: int
    official_2min: int
    official_red: int
    official_blue: int


class OfficialSheetTeam(BaseModel):
    name: str
    score: int
    players: List[OfficialSheetPlayer]


class OfficialSheetProvenance(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    page_count: int


class OfficialSheet(BaseModel):
    snapshot_id: str
    confirmed_date: Date
    home: OfficialSheetTeam
    away: OfficialSheetTeam
    provenance: OfficialSheetProvenance
    pdf_available: bool


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


class CanonicalCutoverUpdate(BaseModel):
    enabled: bool
    reason: str = Field(min_length=1)


class CanonicalRecoveryRequest(BaseModel):
    reason: str = Field(min_length=3)


# ─── Analytical events ─────────────────────────────────────────────────────────

EvidenceState = Literal["confirmed", "no_visible", "ambiguous", "replay"]
CodebookCode = Literal["shot", "seven_meter", "confirmed_assist", "turnover", "recovery", "defensive_action", "foul_sanction", "transition_outcome", "goalkeeper_outcome"]
TurnoverCause = Literal["bad_control", "bad_pass", "interception", "steal", "offensive_foul", "technical_violation", "out_of_play", "other_visible", "ambiguous"]
AnalysisOutcome = Literal["goal", "saved", "missed", "woodwork", "blocked", "goal_conceded"]
CanonicalKind = Literal["shot", "turnover", "recovery", "lineup_change", "goalkeeper_change", "foul_sanction", "other"]
CanonicalFactKind = Literal["observed", "inference"]
ShotZone = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]


class AnalysisEventInput(BaseModel):
    codebook_version: Literal["mvp-1"] = "mvp-1"
    code: CodebookCode
    period: int = Field(default=1, ge=1)
    regulation_seconds: Optional[float] = Field(default=None, ge=0)
    video_timestamp: Optional[float] = Field(default=None, ge=0)
    clock_unverified: bool = False
    team_action: Optional[str] = None
    player_id: Optional[int] = None
    turnover_cause: Optional[TurnoverCause] = None
    outcome: Optional[AnalysisOutcome] = None
    evidence_state: EvidenceState
    source: Optional[str] = None
    angle: Optional[str] = None
    note: Optional[str] = None
    included: bool = True

    @field_validator("turnover_cause")
    @classmethod
    def validate_turnover_cause(cls, value, info):
        code = info.data.get("code")
        if code == "turnover" and value is None:
            raise ValueError("turnover_cause is required for turnover events")
        if code != "turnover" and value is not None:
            raise ValueError("turnover_cause is only valid for turnover events")
        return value


CanonicalEvidenceKind = Literal["fixture", "pdf", "video", "unavailable"]


class CanonicalEvidenceInput(BaseModel):
    kind: CanonicalEvidenceKind
    reference: Optional[str] = None
    scheduled_match_id: Optional[int] = None
    official_snapshot_id: Optional[str] = None
    video_source_id: Optional[int] = None
    video_anchor_seconds: Optional[float] = Field(default=None, ge=0)
    uncertainty: List[str] = Field(default_factory=list)


class CanonicalEventCommand(BaseModel):
    kind: CanonicalKind
    period: int = Field(ge=1)
    regulation_seconds: Optional[float] = Field(default=None, ge=0)
    clock_unverified: bool = False
    team_id: Optional[int] = None
    player_id: Optional[int] = None
    related_player_id: Optional[int] = None
    goalkeeper_id: Optional[int] = None
    outcome: Optional[str] = None
    shot_zone: Optional[ShotZone] = None
    fact_kind: CanonicalFactKind = "observed"
    evidence_state: EvidenceState
    uncertainty: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    evidence: List[CanonicalEvidenceInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shot_zone(self):
        if self.shot_zone is not None and self.kind != "shot":
            raise ValueError("shot_zone is only valid for shot events")
        if self.goalkeeper_id is not None and self.kind != "shot":
            raise ValueError("goalkeeper_id is only valid for shot events")
        return self


class CanonicalEventRevisionInput(CanonicalEventCommand):
    reason: str = Field(min_length=1)


class AnalysisEventCreate(AnalysisEventInput):
    pass


class AnalysisEventUpdate(BaseModel):
    reason: str = Field(min_length=1)
    codebook_version: Optional[Literal["mvp-1"]] = None
    code: Optional[CodebookCode] = None
    period: Optional[int] = Field(default=None, ge=1)
    regulation_seconds: Optional[float] = Field(default=None, ge=0)
    video_timestamp: Optional[float] = Field(default=None, ge=0)
    clock_unverified: Optional[bool] = None
    team_action: Optional[str] = None
    player_id: Optional[int] = None
    turnover_cause: Optional[TurnoverCause] = None
    outcome: Optional[AnalysisOutcome] = None
    evidence_state: Optional[EvidenceState] = None
    source: Optional[str] = None
    angle: Optional[str] = None
    note: Optional[str] = None
    included: Optional[bool] = None


class AnalysisCodebookEntry(BaseModel):
    version: str
    code: str
    category: str

    class Config:
        from_attributes = True


class AnalysisEvent(AnalysisEventInput):
    codebook_version: Literal["mvp-1"] = Field(validation_alias=AliasPath("codebook_entry", "version"))
    code: CodebookCode = Field(validation_alias=AliasPath("codebook_entry", "code"))
    id: int
    match_id: int
    analyst_id: int
    active: bool
    codebook_entry: AnalysisCodebookEntry

    class Config:
        from_attributes = True


class AnalysisEventRevision(BaseModel):
    id: int
    event_id: int
    actor_id: int
    before_payload: Optional[dict]
    after_payload: Optional[dict]
    reason: str

    class Config:
        from_attributes = True


# ─── Video review recovery ─────────────────────────────────────────────────────

AvailabilityState = Literal["loading", "ready", "autoplay_blocked", "unavailable", "embedding_disabled", "restricted", "player_error", "unknown"]
AnalysisProfile = Literal["complete", "classic", "goalkeepers"]


class VideoSourceInput(BaseModel):
    url: str
    availability_state: AvailabilityState = "unknown"


class VideoSource(BaseModel):
    id: int
    original_url: str
    provider: str
    provider_video_id: str
    availability_state: AvailabilityState

    class Config:
        from_attributes = True


class TimeAnchorInput(BaseModel):
    period: int = Field(ge=1)
    video_seconds: float = Field(ge=0)
    regulation_seconds: float = Field(ge=0)
    uncertainty_seconds: float = Field(default=0, ge=0)


class TimeAnchor(TimeAnchorInput):
    id: int

    class Config:
        from_attributes = True


TimeSegmentCoverage = Literal["playable", "pause", "cut", "replay", "halftime", "offset"]


class TimeSegmentInput(BaseModel):
    period: int = Field(ge=1)
    video_start_seconds: float = Field(ge=0)
    video_end_seconds: float = Field(gt=0)
    regulation_start_seconds: Optional[float] = Field(default=None, ge=0)
    regulation_end_seconds: Optional[float] = Field(default=None, ge=0)
    uncertainty_seconds: float = Field(default=0, ge=0)
    coverage: TimeSegmentCoverage
    clock_unverified: bool = False

    @model_validator(mode="after")
    def validate_coverage(self):
        if self.video_end_seconds <= self.video_start_seconds:
            raise ValueError("Video segment end must be after its start")
        regulation_range = (self.regulation_start_seconds, self.regulation_end_seconds)
        if self.coverage == "playable":
            if None in regulation_range or self.regulation_end_seconds <= self.regulation_start_seconds:
                raise ValueError("Playable segments require an increasing regulation range")
            if self.clock_unverified:
                raise ValueError("Playable segments must have a verified clock")
        elif any(value is not None for value in regulation_range) or not self.clock_unverified:
            raise ValueError("Non-playable segments must be clock-unverified without a regulation range")
        return self


class TimeSegment(TimeSegmentInput):
    id: int

    class Config:
        from_attributes = True


class AnalysisSessionUpdate(BaseModel):
    mode: Literal["live", "video"] = "live"
    profile: AnalysisProfile = "complete"
    source: Optional[VideoSourceInput] = None
    video_position_seconds: Optional[float] = Field(default=None, ge=0)
    clock_start_video_seconds: Optional[float] = Field(default=None, ge=0)
    angle: Optional[str] = None
    filters: dict = Field(default_factory=dict)
    draft: dict = Field(default_factory=dict)
    queue: List[dict] = Field(default_factory=list)
    anchors: Optional[List[TimeAnchorInput]] = None
    time_segments: Optional[List[TimeSegmentInput]] = None


class AnalysisSession(AnalysisSessionUpdate):
    id: int
    match_id: int
    analyst_id: int
    source: Optional[VideoSource] = Field(default=None, validation_alias="video_source")
    anchors: List[TimeAnchor] = []
    time_segments: List[TimeSegment] = []


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


# ─── PDF preview ──────────────────────────────────────────────────────────────

class PDFPlayerPreview(BaseModel):
    number: int
    name: str
    goals: int
    yellow: int
    two_min: int
    red: int
    blue: int


class PDFTeamPreview(BaseModel):
    name: str
    players: List[PDFPlayerPreview]


class PDFProvenance(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    page_count: int


class PDFFieldSource(BaseModel):
    page: int
    table: Optional[int] = None
    label: str


class PDFFieldEvidence(BaseModel):
    value: str | int | None
    raw: Optional[str] = None
    source: Optional[PDFFieldSource] = None
    confidence: Literal["high", "low", "unresolved"]
    warnings: List[str]


class PDFPreview(BaseModel):
    match_info: dict[str, str | int]
    home_team: PDFTeamPreview
    away_team: PDFTeamPreview
    provenance: PDFProvenance
    warnings: List[str]
    fields: dict[str, PDFFieldEvidence]


class PDFConfirmedTeam(BaseModel):
    name: str = Field(min_length=1)
    existing_team_id: Optional[int] = None


class PDFConfirmedPlayer(BaseModel):
    name: str = Field(min_length=1)
    jersey_number: int = Field(ge=1)
    existing_player_id: Optional[int] = None
    official_goals: int = Field(default=0, ge=0)
    official_yellow: int = Field(default=0, ge=0)
    official_2min: int = Field(default=0, ge=0)
    official_red: int = Field(default=0, ge=0)
    official_blue: int = Field(default=0, ge=0)


class PDFImportConfirmation(BaseModel):
    date: Date
    home_team: PDFConfirmedTeam
    away_team: PDFConfirmedTeam
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    home_players: List[PDFConfirmedPlayer] = []
    away_players: List[PDFConfirmedPlayer] = []


class PDFImportResult(BaseModel):
    match_id: int
    snapshot_id: str


# ─── Fixture-linked PDF confirmation ──────────────────────────────────────────

ScoreReconciliation = Literal["match", "mismatch", "unknown"]
FixtureCompatibility = Literal["compatible", "incompatible", "unresolved"]


class FixtureRegistrationRead(BaseModel):
    id: int
    display_name: str
    variant: Optional[str] = None


class FixtureStageRead(BaseModel):
    id: int
    season_year: int
    name: str
    category: str
    division: str
    gender: str


class ScheduledFixtureRead(BaseModel):
    fixture_key: str
    stage: FixtureStageRead
    home_registration: FixtureRegistrationRead
    away_registration: FixtureRegistrationRead
    scheduled_date: Optional[Date] = None
    venue: Optional[str] = None
    court: Optional[str] = None
    match_time: Optional[str] = None
    source_home_score: Optional[int] = None
    source_away_score: Optional[int] = None
    result_status: Literal["unreported", "reported", "approved", "disputed", "confirmed"]
    linked_match_id: Optional[int] = None
    official_snapshot_id: Optional[str] = None
    is_preloaded: bool = False
    youtube_link: str = ""
    roster_status: Literal["not_confirmed", "needs_identity_resolution", "ready"] = "not_confirmed"
    unresolved_roster_players: int = 0


class FixtureSideCompatibility(BaseModel):
    status: FixtureCompatibility
    expected_name: str
    expected_variant: Optional[str] = None
    parsed_name: Optional[str] = None
    parsed_variant: Optional[str] = None


class FixturePreviewResult(BaseModel):
    fixture: ScheduledFixtureRead
    preview: PDFPreview
    home_compatibility: FixtureSideCompatibility
    away_compatibility: FixtureSideCompatibility
    score_reconciliation: ScoreReconciliation


class FixtureConfirmedPlayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    jersey_number: int = Field(ge=1)
    existing_player_id: Optional[int] = Field(default=None, gt=0)
    official_goals: int = Field(default=0, ge=0)
    official_yellow: int = Field(default=0, ge=0)
    official_2min: int = Field(default=0, ge=0)
    official_red: int = Field(default=0, ge=0)
    official_blue: int = Field(default=0, ge=0)


class FixtureConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_team_id: int = Field(gt=0)
    away_team_id: int = Field(gt=0)
    home_players: List[FixtureConfirmedPlayer] = Field(default_factory=list)
    away_players: List[FixtureConfirmedPlayer] = Field(default_factory=list)
    acknowledge_score_mismatch: bool = False
    acknowledge_name_mismatch: bool = False


class FixtureConfirmResult(BaseModel):
    match_id: int
    snapshot_id: str
    reused: bool = False


# ─── Match-scoped official PDF confirmation ──────────────────────────────────

class MatchSideCompatibility(BaseModel):
    status: FixtureCompatibility
    expected_name: Optional[str] = None
    parsed_name: Optional[str] = None


class MatchPDFPreviewResult(BaseModel):
    match_id: int
    preview: PDFPreview
    home_compatibility: MatchSideCompatibility
    away_compatibility: MatchSideCompatibility
    score_reconciliation: ScoreReconciliation
    date_reconciliation: ScoreReconciliation
    warnings: List[str] = []


class MatchPDFConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_players: List[FixtureConfirmedPlayer] = Field(default_factory=list)
    away_players: List[FixtureConfirmedPlayer] = Field(default_factory=list)
    acknowledge_mismatches: bool = False


class MatchPDFConfirmResult(BaseModel):
    match_id: int
    snapshot_id: str
    reused: bool = False


class FixtureRosterPlayerRead(BaseModel):
    id: int
    side: Literal["home", "away"]
    name: str
    jersey_number: int
    player_id: Optional[int] = None
    candidates: List[Player] = []


class FixtureRosterRead(BaseModel):
    fixture: ScheduledFixtureRead
    players: List[FixtureRosterPlayerRead]


class FixtureRosterResolution(BaseModel):
    snapshot_player_id: int = Field(gt=0)
    existing_player_id: Optional[int] = Field(default=None, gt=0)
    create_player: bool = False

    @model_validator(mode="after")
    def validate_choice(self):
        if (self.existing_player_id is not None) == self.create_player:
            raise ValueError("choose exactly one of existing_player_id or create_player")
        return self


class FixtureRosterResolveRequest(BaseModel):
    resolutions: List[FixtureRosterResolution] = Field(default_factory=list)


class FixtureRosterResolveResult(BaseModel):
    match_id: int
    roster_status: Literal["needs_identity_resolution", "ready"]
    unresolved_roster_players: int


# ─── Reviewed report packages ─────────────────────────────────────────────────

PackageActionKind = Literal["keep", "do", "change"]


class ReportPackageEvidenceInput(BaseModel):
    reference: str = Field(min_length=1)
    period: int = Field(ge=1)
    regulation_seconds: Optional[float] = Field(default=None, ge=0)
    clock_unverified: bool = False
    public_observation: Optional[str] = None
    public_approved: bool = False


class ReportPackageInput(BaseModel):
    coaching_question: str = Field(min_length=1)
    pattern_statement: str = Field(min_length=1)
    action_kind: PackageActionKind
    action_text: str = Field(min_length=1)
    uncertainty_disclosure: str = Field(min_length=1)
    metrics: dict = Field(default_factory=dict)
    reconciliation: List[dict] = Field(default_factory=list)
    source_label: Optional[str] = None
    source_status: Optional[str] = None
    canonical_event_ids: List[int] = Field(default_factory=list)
    evidence: List[ReportPackageEvidenceInput] = Field(default_factory=list)


class ReportPackageCreate(ReportPackageInput):
    pass


class ReportPackageUpdate(ReportPackageInput):
    pass


class ReportPackageEvidence(ReportPackageEvidenceInput):
    id: int

    class Config:
        from_attributes = True


class ReviewedReportPackage(ReportPackageInput):
    id: int
    match_id: int
    report_version: int
    schema_version: str
    approved_at: Optional[datetime] = None
    evidence: List[ReportPackageEvidence] = []

    class Config:
        from_attributes = True


class RecoveryArtifactStatus(BaseModel):
    artifact_type: Literal["postgres_dump", "imported_pdf_export"]
    location: str
    attested_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecoveryArtifactAttestation(BaseModel):
    location: str = Field(min_length=1)


class ReportPublicationStatus(BaseModel):
    package_id: int
    report_version: int
    status: Literal["not_ready", "ready", "publishing", "published", "failed"]
    missing_recovery_artifacts: List[str] = []
    recovery_artifacts: List[RecoveryArtifactStatus] = []
    published_at: Optional[datetime] = None
    failure_message: Optional[str] = None
    public_url: Optional[str] = None


# ─── Goalkeeper shots ─────────────────────────────────────────────────────────

GoalkeeperOriginZone = Literal[
    "6m_left", "6m_center", "6m_right",
    "9m_left", "9m_center", "9m_right",
    "wing_left", "wing_right", "seven_meter", "counter",
]
GoalkeeperTargetZone = Literal[
    "high_left", "high_center", "high_right",
    "low_left", "low_center", "low_right",
]
GoalkeeperShotType = Literal["power", "spin", "lob"]
GoalkeeperOutcome = Literal["goal", "saved", "missed", "woodwork", "blocked"]


class GoalkeeperShotCreate(BaseModel):
    shooter_player_id: Optional[int] = None
    shooter_label: Optional[str] = Field(default=None, max_length=16)
    period: Optional[int] = None
    video_timestamp: Optional[float] = Field(default=None, ge=0)
    origin_zone: Optional[GoalkeeperOriginZone] = None
    target_zone: Optional[GoalkeeperTargetZone] = None
    shot_type: Optional[GoalkeeperShotType] = None
    outcome: Optional[GoalkeeperOutcome] = None
    note: Optional[str] = None


class GoalkeeperShot(GoalkeeperShotCreate):
    id: int
    match_id: int
    created_at: datetime

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


# ─── Competition Layer Schemas ──────────────────────────────────────────────────────


class SeasonBase(BaseModel):
    year: int
    description: Optional[str] = None


class SeasonCreate(SeasonBase):
    pass


class SeasonUpdate(BaseModel):
    year: Optional[int] = None
    description: Optional[str] = None


class Season(SeasonBase):
    id: int

    class Config:
        from_attributes = True


class TournamentStageBase(BaseModel):
    name: str
    category: str
    division: str
    gender: str


class TournamentStageCreate(TournamentStageBase):
    season_id: int


class TournamentStageUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    division: Optional[str] = None
    gender: Optional[str] = None


class TournamentStage(TournamentStageBase):
    id: int
    season_id: int

    class Config:
        from_attributes = True


class ClubBase(BaseModel):
    name: str
    short_name: Optional[str] = None


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None


class Club(ClubBase):
    id: int

    class Config:
        from_attributes = True


class CompetitionTeamBase(BaseModel):
    club_id: int
    stage_id: int
    variant: Optional[str] = Field(default=None, max_length=2, validation_alias=AliasChoices("variant", "suffix"))


class CompetitionTeamCreate(CompetitionTeamBase):
    pass


class CompetitionTeamUpdate(BaseModel):
    club_id: Optional[int] = None
    stage_id: Optional[int] = None
    variant: Optional[str] = Field(default=None, max_length=2, validation_alias=AliasChoices("variant", "suffix"))


class CompetitionTeam(CompetitionTeamBase):
    id: int
    club: Optional[Club] = None
    stage: Optional[TournamentStage] = None

    class Config:
        from_attributes = True


class TeamRegistrationBase(BaseModel):
    competition_team_id: int
    stage_id: int
    group: Optional[str] = None
    seed_order: Optional[int] = None


class TeamRegistrationCreate(TeamRegistrationBase):
    pass


class TeamRegistrationUpdate(BaseModel):
    competition_team_id: Optional[int] = None
    stage_id: Optional[int] = None
    group: Optional[str] = None
    seed_order: Optional[int] = None


class TeamRegistration(TeamRegistrationBase):
    id: int
    competition_team: Optional[CompetitionTeam] = None
    stage: Optional[TournamentStage] = None

    class Config:
        from_attributes = True


class RoundBase(BaseModel):
    stage_id: int
    round_number: int
    date_range_start: Optional[Date] = None
    date_range_end: Optional[Date] = None


class RoundCreate(RoundBase):
    pass


class RoundUpdate(BaseModel):
    stage_id: Optional[int] = None
    round_number: Optional[int] = None
    date_range_start: Optional[Date] = None
    date_range_end: Optional[Date] = None


class Round(RoundBase):
    id: int
    stage: Optional[TournamentStage] = None

    class Config:
        from_attributes = True


MatchStatus = Literal["scheduled", "played", "postponed", "cancelled"]
FixtureResultStatus = Literal["unreported", "reported", "approved", "disputed", "confirmed"]


class ScheduledMatchBase(BaseModel):
    stage_id: int
    round_id: int
    home_registration_id: int
    away_registration_id: int
    scheduled_date: Optional[Date] = None
    venue: Optional[str] = None
    court: Optional[str] = None
    match_time: Optional[str] = None
    match_number_label: str
    status: MatchStatus = "scheduled"


class ScheduledMatchCreate(ScheduledMatchBase):
    pass


class ScheduledMatchUpdate(BaseModel):
    stage_id: Optional[int] = None
    round_id: Optional[int] = None
    home_registration_id: Optional[int] = None
    away_registration_id: Optional[int] = None
    scheduled_date: Optional[Date] = None
    venue: Optional[str] = None
    court: Optional[str] = None
    match_time: Optional[str] = None
    match_number_label: Optional[str] = None
    status: Optional[MatchStatus] = None


class ScheduledMatch(ScheduledMatchBase):
    id: int
    fixture_key: str
    source_home_score: Optional[int] = None
    source_away_score: Optional[int] = None
    result_status: FixtureResultStatus = "unreported"
    stage: Optional[TournamentStage] = None
    round: Optional[Round] = None
    home_registration: Optional[TeamRegistration] = None
    away_registration: Optional[TeamRegistration] = None

    class Config:
        from_attributes = True


class FixtureImportEntry(BaseModel):
    id: int
    fixture_import_id: int
    entry_key: str
    kind: Literal["match", "bye"]
    raw_entry: dict
    scheduled_match_id: Optional[int] = None

    class Config:
        from_attributes = True


class FixtureImport(BaseModel):
    id: int
    stage_id: int
    source_label: str
    captured_at: datetime
    source_sha256: str
    payload: dict
    entries: List[FixtureImportEntry] = []

    class Config:
        from_attributes = True


class StageRosterBase(BaseModel):
    registration_id: int
    player_id: int
    jersey_number: int = Field(ge=1)


class StageRosterCreate(StageRosterBase):
    pass


class StageRosterUpdate(BaseModel):
    registration_id: Optional[int] = None
    player_id: Optional[int] = None
    jersey_number: Optional[int] = Field(default=None, ge=1)


class StageRoster(StageRosterBase):
    id: int
    registration: Optional[TeamRegistration] = None
    player: Optional[Player] = None

    class Config:
        from_attributes = True


# ─── Composite Admin Payload ────────────────────────────────────────────────────────


class FixtureAdminPayload(BaseModel):
    season: SeasonCreate
    stages: List[TournamentStageCreate] = []
    clubs: List[ClubCreate] = []
    competition_teams: List[CompetitionTeamCreate] = []
    registrations: List[TeamRegistrationCreate] = []
    rounds: List[RoundCreate] = []
    scheduled_matches: List[ScheduledMatchCreate] = []


class PDFImportConfirmationFixture(BaseModel):
    scheduled_match_id: int
    home_registration_id: int
    away_registration_id: int
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    home_players: List[PDFConfirmedPlayer] = []
    away_players: List[PDFConfirmedPlayer] = []
