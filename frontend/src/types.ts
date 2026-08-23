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
  date: string
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
  tournament: Tournament | null
  home_team: Team | null
  away_team: Team | null
  squad: MatchSquad[]
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
