// ─── Auth types ───────────────────────────────────────────────────────────────

export type UserRole = 'superadmin' | 'admin' | 'analyst'

export interface UserRead {
  id: number
  email: string
  full_name: string
  role: UserRole
  club_id: number | null
  is_active: boolean
  must_change_password: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserRead
}

// ─── Domain types (mirror backend schemas) ────────────────────────────────────

export interface Tournament {
  id: number
  name: string
  category: string
  year: number
}

export interface Team {
  id: number
  name: string
  club_name: string | null
  category: string | null
}

export interface Player {
  id: number
  name: string
  default_jersey_number: number | null
  global_position: string | null
  team_id: number | null
  team: Team | null
}

export interface MatchSquad {
  id: number
  match_id: number
  player_id: number
  jersey_number: number
  is_goalkeeper: boolean
  official_goals: number
  official_yellow: number
  official_2min: number
  official_red: number
  official_blue: number
  player: Player | null
}

export interface Match {
  id: number
  tournament_id: number | null
  date: string | null
  home_team_id: number | null
  away_team_id: number | null
  youtube_link: string | null
  main_team_focus: string
  venue: string | null
  court: string | null
  match_time: string | null
  category_label: string | null
  match_number_label: string | null
  home_score: number
  away_score: number
  pdf_file_path: string | null
  canonical_analysis_enabled: boolean
  tournament: Tournament | null
  home_team: Team | null
  away_team: Team | null
  squad: MatchSquad[]
  origin: 'manual' | 'fixture' | 'legacy'
  created_by_user_id: number | null
}

export interface Event {
  id: number
  match_id: number
  game_timestamp: number
  period: number | null
  team_action: string
  player_id: number | null
  action_type: string
  result: string | null
  shot_zone: string | null
  loss_detail: string | null
  attack_phase: string | null
  assist_player_id: number | null
  goalkeeper_id: number | null
  sub_in_player_id: number | null
  sub_out_player_id: number | null
  transition_type: string | null
  transition_result: string | null
  sanction_type: string | null
  sanction_target: string | null
  player: Player | null
  assist_player: Player | null
  goalkeeper: Player | null
  sub_in_player: Player | null
  sub_out_player: Player | null
}

export interface Clip {
  id: number
  match_id: number
  video_start: number
  video_end: number
  title: string
  player_tags: string | null
}

export interface OfficialSheetPlayer {
  player_id: number | null
  name: string
  jersey_number: number
  official_goals: number
  official_yellow: number
  official_2min: number
  official_red: number
  official_blue: number
}

export interface OfficialSheet {
  snapshot_id: string
  confirmed_date: string
  home: { name: string; score: number; players: OfficialSheetPlayer[] }
  away: { name: string; score: number; players: OfficialSheetPlayer[] }
  provenance: { filename: string; content_type: string; size_bytes: number; sha256: string; page_count: number }
  pdf_available: boolean
}

export interface MatchPDFPreviewResult {
  match_id: number
  preview: PDFPreview
  home_compatibility: { status: 'compatible' | 'incompatible' | 'unresolved'; expected_name: string | null; parsed_name: string | null }
  away_compatibility: { status: 'compatible' | 'incompatible' | 'unresolved'; expected_name: string | null; parsed_name: string | null }
  score_reconciliation: 'match' | 'mismatch' | 'unknown'
  date_reconciliation: 'match' | 'mismatch' | 'unknown'
  warnings: string[]
}

export interface MatchPDFConfirmation {
  home_players: FixtureConfirmedPlayer[]
  away_players: FixtureConfirmedPlayer[]
  acknowledge_mismatches: boolean
}

export interface MatchPDFConfirmResult { match_id: number; snapshot_id: string; reused: boolean }

export type AnalysisCode =
  | 'shot' | 'seven_meter' | 'confirmed_assist' | 'turnover' | 'recovery'
  | 'defensive_action' | 'foul_sanction' | 'transition_outcome' | 'goalkeeper_outcome'

export type EvidenceState = 'confirmed' | 'no_visible' | 'ambiguous' | 'replay'
export type AnalysisOutcome = 'goal' | 'saved' | 'missed' | 'woodwork' | 'blocked' | 'goal_conceded'

export interface AnalysisEventInput {
  codebook_version: 'mvp-1'
  code: AnalysisCode
  period: number
  regulation_seconds: number | null
  video_timestamp: number | null
  clock_unverified: boolean
  team_action: string | null
  player_id: number | null
  turnover_cause: string | null
  outcome: AnalysisOutcome | null
  evidence_state: EvidenceState
  source: string | null
  angle: string | null
  note: string | null
  included: boolean
}

export interface AnalysisEvent extends AnalysisEventInput {
  id: number
  match_id: number
  analyst_id: number
  active: boolean
  codebook_entry: { version: string; code: string; category: string }
}

export type CanonicalEventKind = 'shot' | 'turnover' | 'recovery' | 'lineup_change' | 'goalkeeper_change' | 'foul_sanction' | 'other'
export type ShotZone = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9

export interface CanonicalEventCommand {
  kind: CanonicalEventKind
  period: number
  regulation_seconds: number | null
  clock_unverified: boolean
  team_id: number | null
  player_id: number | null
  related_player_id?: number | null
  goalkeeper_id?: number | null
  outcome: string | null
  shot_zone?: ShotZone | null
  fact_kind: 'observed'
  evidence_state: EvidenceState
  uncertainty: string[]
  note: string | null
  evidence?: CanonicalEvidenceInput[]
}

export interface CanonicalEvidenceInput {
  kind: 'fixture' | 'pdf' | 'video' | 'unavailable'
  reference?: string | null
  scheduled_match_id?: number | null
  official_snapshot_id?: string | null
  video_source_id?: number | null
  video_anchor_seconds?: number | null
  uncertainty: string[]
}

export interface CanonicalEventRevisionInput extends CanonicalEventCommand {
  reason: string
}

export interface CanonicalEvidence extends CanonicalEvidenceInput {
  id: number
}

export interface CanonicalEvent {
  id: number
  sequence: number
  active: boolean
  payload: CanonicalEventCommand & { roster_source?: string; related_player_roster_source?: string }
  revision?: number
  actor_id?: number
  reason?: string
  evidence?: CanonicalEvidence[]
}

export interface CanonicalPlayerProjection {
  player: { id: number; name: string | null; team_id: number | null; roster_source: string }
  filters: { team_id: number | null; period: number | null; from_regulation_seconds: number | null; to_regulation_seconds: number | null }
  participation: { on: number; off: number; substitution: number; evidence: CanonicalEvent[] }
  metrics: { saves: number; goals_conceded: number; save_rate: { numerator: number; denominator: number; value: number } | null }
  discipline: { yellow: number; two_minute: number; red: number; evidence: CanonicalEvent[] }
  shot_map: { zones: Record<string, number>; recorded: number; missing_zone: number; goalkeeper_unknown: number; excluded: number; unknown: number; clock_unverified: number }
  evidence: Array<CanonicalEvent & { bucket?: string }>
  unfiltered_context: { canonical_metrics: ReviewedMetrics; reconciliation: { official: ReviewedMetrics['official']; discrepancies: ReviewedMetrics['reconciliation']; discipline: NonNullable<ReviewedMetrics['discipline']> } }
}

export type WarningStatus = 'exact' | 'within_tolerance' | 'missing_in_canonical' | 'missing_in_official' | 'not_comparable'
export type WarningMetric = 'goals' | 'yellow' | 'two_minute' | 'red' | 'blue'

export interface WarningComparison {
  canonical: number | null
  official: number | null
  status: WarningStatus
  tolerance: 0
  canonical_event_ids: number[]
  evidence_ids: number[]
}

export interface WarningsSummary {
  match_id: number
  official_snapshot_id: string | null
  players: Array<{
    player: { id: number | null; name: string; jersey_number: number | null; side: 'home' | 'away' | null }
    metrics: Record<WarningMetric, WarningComparison>
  }>
  match_totals: { metrics: Record<WarningMetric, WarningComparison> }
  limitations: Array<{ check: 'goal_timestamps' | 'card_timestamps' | 'goalkeeper_substitutions'; status: 'not_comparable'; reason: string }>
}

export interface CanonicalMatchState {
  analytical_score: Record<string, number>
  possession: { team_id: number; start_basis: string; terminal_basis: string | null; unresolved: boolean } | null
  active_goalkeepers: Record<string, number | null>
  player_states: Record<string, string>
  discipline: Array<{ event_id: number; team_id: number | null; player_id: number | null; sanction: string; uncertainty: string[] }>
}

export type VideoAvailabilityState = 'loading' | 'ready' | 'autoplay_blocked' | 'unavailable' | 'embedding_disabled' | 'restricted' | 'player_error' | 'unknown'
export type AnalysisProfile = 'complete' | 'classic' | 'goalkeepers'

export interface VideoSource {
  id: number
  original_url: string
  provider: string
  provider_video_id: string
  availability_state: VideoAvailabilityState
}

export interface TimeAnchor {
  id: number
  period: number
  video_seconds: number
  regulation_seconds: number
  uncertainty_seconds: number
}

export type TimeSegmentCoverage = 'playable' | 'pause' | 'cut' | 'replay' | 'halftime' | 'offset'

export interface TimeSegment {
  id: number
  period: number
  video_start_seconds: number
  video_end_seconds: number
  regulation_start_seconds: number | null
  regulation_end_seconds: number | null
  uncertainty_seconds: number
  coverage: TimeSegmentCoverage
  clock_unverified: boolean
}

export interface AnalysisSession {
  id: number
  match_id: number
  analyst_id: number
  mode: 'live' | 'video'
  profile: AnalysisProfile
  source: VideoSource | null
  video_position_seconds: number | null
  clock_start_video_seconds: number | null
  angle: string | null
  filters: Record<string, unknown>
  draft: Partial<AnalysisEventInput>
  queue: Array<Record<string, unknown>>
  anchors: TimeAnchor[]
  time_segments: TimeSegment[]
}

export interface AnalysisSessionUpdate {
  mode: 'live' | 'video'
  profile: AnalysisProfile
  source?: { url: string; availability_state: VideoAvailabilityState } | null
  video_position_seconds: number | null
  clock_start_video_seconds: number | null
  angle: string | null
  filters: Record<string, unknown>
  draft: Partial<AnalysisEventInput>
  queue: Array<Record<string, unknown>>
  anchors: Array<Omit<TimeAnchor, 'id'>>
  time_segments?: Array<Omit<TimeSegment, 'id'>>
}

export interface ReviewedMetric {
    name: string
    count: number
    numerator: number
    denominator: number | 'not_applicable'
    excluded: number
    unknown: number
    clock_unverified: number
    evidence?: Array<{ event_id: number; revision_id: number }>
}

export interface ReviewedMetrics {
  metrics: Record<string, ReviewedMetric>
  official: { snapshot_id: string | number; home_score: number; away_score: number } | null
  reconciliation: Array<{
      side: 'home' | 'away'
      official: number
      analytical: number
      discrepancy: number
    }>
    discipline?: Array<{
      team_id: number
      side: 'home' | 'away'
      official: { yellow: number; two_minute: number; red: number }
      observed: { yellow: number; two_minute: number; red: number }
      status: 'match' | 'mismatch'
      coverage: { eligible_discipline_events: number }
    }>
  eligibility?: { eligible: number; excluded: number; unknown: number; clock_unverified: number; unresolved: number }
  evidence?: Record<string, Array<{ id: number; kind: string; reference: string; uncertainty: string[] }>>
}

// Reviewed packages intentionally expose only publication-safe evidence fields.
export type ReportPackageActionKind = 'keep' | 'do' | 'change'

export interface ReportPackageEvidenceInput {
  reference: string
  period: number
  regulation_seconds: number | null
  clock_unverified: boolean
  public_observation: string | null
  public_approved: boolean
}

export interface ReportPackageInput {
  coaching_question: string
  pattern_statement: string
  action_kind: ReportPackageActionKind
  action_text: string
  uncertainty_disclosure: string
  metrics: Record<string, unknown>
  reconciliation: Array<Record<string, unknown>>
  source_label: string | null
  source_status: string | null
  canonical_event_ids?: number[]
  evidence: ReportPackageEvidenceInput[]
}

export interface ReviewedReportPackage extends ReportPackageInput {
  id: number
  match_id: number
  report_version: number
  schema_version: string
  approved_at: string | null
  evidence: Array<ReportPackageEvidenceInput & { id: number }>
}

export type PublicationState = 'not_ready' | 'ready' | 'publishing' | 'published' | 'failed'

export interface RecoveryArtifactStatus {
  artifact_type: 'postgres_dump' | 'imported_pdf_export'
  location: string
  attested_at: string | null
}

export interface ReportPublicationStatus {
  package_id: number
  report_version: number
  status: PublicationState
  missing_recovery_artifacts: string[]
  recovery_artifacts: RecoveryArtifactStatus[]
  published_at: string | null
  failure_message: string | null
  public_url: string | null
}

export interface PDFPlayerPreview {
  number: number
  name: string
  goals: number
  yellow: number
  two_min: number
  red: number
  blue: number
}

export interface PDFTeamPreview {
  name: string
  players: PDFPlayerPreview[]
}

export interface PDFProvenance {
  filename: string
  content_type: string
  size_bytes: number
  sha256: string
  page_count: number
}

export interface PDFPreview {
  match_info: Record<string, string | number>
  home_team: PDFTeamPreview
  away_team: PDFTeamPreview
  provenance: PDFProvenance
  warnings: string[]
}

export interface PDFImportConfirmation {
  date: string
  home_team: { name: string; existing_team_id: number | null }
  away_team: { name: string; existing_team_id: number | null }
  home_score: number
  away_score: number
  home_players: PDFConfirmedPlayer[]
  away_players: PDFConfirmedPlayer[]
}

export interface PDFConfirmedPlayer {
  name: string
  jersey_number: number
  existing_player_id: number | null
  official_goals: number
  official_yellow: number
  official_2min: number
  official_red: number
  official_blue: number
}

export interface PDFImportResult {
  match_id: number
  snapshot_id: string
}

export type FixtureCompatibility = 'compatible' | 'incompatible' | 'unresolved'
export type ScoreReconciliation = 'match' | 'mismatch' | 'unknown'

export interface FixtureRegistration {
  id: number
  display_name: string
  variant: string | null
}

export interface FixtureStage {
  id: number
  season_year: number
  name: string
  category: string
  division: string
  gender: string
}

export interface ScheduledFixture {
  fixture_key: string
  stage: FixtureStage
  home_registration: FixtureRegistration
  away_registration: FixtureRegistration
  scheduled_date: string | null
  venue: string | null
  court: string | null
  match_time: string | null
  source_home_score: number | null
  source_away_score: number | null
  result_status: 'unreported' | 'reported' | 'approved' | 'disputed' | 'confirmed'
  linked_match_id: number | null
  official_snapshot_id: string | null
  is_preloaded: boolean
  youtube_link: string
  roster_status: 'not_confirmed' | 'needs_identity_resolution' | 'ready'
  unresolved_roster_players: number
}

export interface FixtureRosterPlayer {
  id: number
  side: 'home' | 'away'
  name: string
  jersey_number: number
  player_id: number | null
  candidates: Player[]
}

export interface FixtureRoster {
  fixture: ScheduledFixture
  players: FixtureRosterPlayer[]
}

export interface FixtureRosterResolution {
  snapshot_player_id: number
  existing_player_id?: number
  create_player: boolean
}

export interface FixtureSideCompatibility {
  status: FixtureCompatibility
  expected_name: string
  expected_variant: string | null
  parsed_name: string | null
  parsed_variant: string | null
}

export interface FixturePreviewResult {
  fixture: ScheduledFixture
  preview: PDFPreview
  home_compatibility: FixtureSideCompatibility
  away_compatibility: FixtureSideCompatibility
  score_reconciliation: ScoreReconciliation
}

export interface FixtureConfirmedPlayer {
  name: string
  jersey_number: number
  existing_player_id?: number | null
  official_goals: number
  official_yellow: number
  official_2min: number
  official_red: number
  official_blue: number
}

export interface FixtureConfirmation {
  home_team_id: number
  away_team_id: number
  home_players: FixtureConfirmedPlayer[]
  away_players: FixtureConfirmedPlayer[]
  acknowledge_score_mismatch: boolean
}

export interface FixtureConfirmResult {
  match_id: number
  snapshot_id: string
  reused: boolean
}

// ─── Wizard state ─────────────────────────────────────────────────────────────

export type TagStep =
  | 'idle'           // Esperando selección de jugador
  | 'action'         // Seleccionar acción
  | 'shot_result'    // Resultado de lanzamiento
  | 'shot_zone'      // Zona de lanzamiento
  | 'assist'         // Seleccionar asistente (tras gol)
  | 'loss_detail'    // Detalle de pérdida
  | 'foul_type'      // Tipo de falta
  | 'sanction_type'  // Tipo de sanción
  | 'sanction_target'// Objetivo de la sanción
  | 'sub_out'        // Jugador que sale
  | 'sub_in'         // Jugador que entra

export interface TagState {
  step: TagStep
  playerId: number | null
  teamAction: string
  actionType: string | null
  result: string | null
  shotZone: string | null
  lossDetail: string | null
  foulType: string | null
  sanctionType: string | null
  sanctionTarget: string | null
  assistPlayerId: number | null
  subOutPlayerId: number | null
  subInPlayerId: number | null
}

export const INITIAL_TAG_STATE: TagState = {
  step: 'idle',
  playerId: null,
  teamAction: '',
  actionType: null,
  result: null,
  shotZone: null,
  lossDetail: null,
  foulType: null,
  sanctionType: null,
  sanctionTarget: null,
  assistPlayerId: null,
  subOutPlayerId: null,
  subInPlayerId: null,
}

// ─── Goalkeeper mode ──────────────────────────────────────────────────────────

export type GoalkeeperOriginZone =
  | '6m_left' | '6m_center' | '6m_right'
  | '9m_left' | '9m_center' | '9m_right'
  | 'wing_left' | 'wing_right' | 'seven_meter' | 'counter'

export type GoalkeeperTargetZone =
  | 'high_left' | 'high_center' | 'high_right'
  | 'low_left' | 'low_center' | 'low_right'

export type GoalkeeperShotType = 'power' | 'spin' | 'lob'

export type GoalkeeperOutcome = 'goal' | 'saved' | 'missed' | 'woodwork' | 'blocked'

export interface GoalkeeperShotCreate {
  shooter_player_id: number | null
  shooter_label: string | null
  period: number | null
  video_timestamp: number | null
  origin_zone: GoalkeeperOriginZone | null
  target_zone: GoalkeeperTargetZone | null
  shot_type: GoalkeeperShotType | null
  outcome: GoalkeeperOutcome | null
  note: string | null
}

export interface GoalkeeperShot extends GoalkeeperShotCreate {
  id: number
  match_id: number
  created_at: string
}
