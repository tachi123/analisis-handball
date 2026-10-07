import axios from 'axios'
import type {
  Tournament, Team, Player, Match, MatchSquad, Event, Clip, PDFImportConfirmation, PDFImportResult, PDFPreview, MatchPDFConfirmation, MatchPDFConfirmResult, MatchPDFPreviewResult,
  TokenResponse, UserRead, AnalysisEvent, AnalysisEventInput, CanonicalEvent, CanonicalEventCommand, CanonicalEventRevisionInput, CanonicalMatchState, ReviewedMetrics, AnalysisSession, AnalysisSessionUpdate,
  ReportPackageInput, ReportPublicationStatus, ReviewedReportPackage,
    GoalkeeperShot, GoalkeeperShotCreate, FixtureConfirmation, FixtureConfirmResult, FixturePreviewResult, FixtureRoster, FixtureRosterResolution, ScheduledFixture, CanonicalPlayerProjection, WarningsSummary, OfficialSheet,
} from '../types'

const http = axios.create({ baseURL: `${import.meta.env.VITE_API_URL ?? ''}/api/v1` })

// ─── JWT interceptor ──────────────────────────────────────────────────────────
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      const base = import.meta.env.BASE_URL.replace(/\/$/, '')
      window.location.href = `${base}/login`
    }
    return Promise.reject(error)
  },
)

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const login = (email: string, password: string) =>
  http.post<TokenResponse>('/auth/login', { email, password }).then(r => r.data)
export const getMe = () => http.get<UserRead>('/auth/me').then(r => r.data)
export const changePassword = (current_password: string, new_password: string) =>
  http.put<UserRead>('/auth/change-password', { current_password, new_password }).then(r => r.data)
export const listUsers = () => http.get<UserRead[]>('/auth/users').then(r => r.data)
export const createUser = (d: { email: string; full_name: string; password: string; role: string }) =>
  http.post<UserRead>('/auth/users', d).then(r => r.data)

// ─── Tournaments ──────────────────────────────────────────────────────────────
export const getTournaments = () => http.get<Tournament[]>('/tournaments/').then(r => r.data)
export const createTournament = (d: Omit<Tournament, 'id'>) => http.post<Tournament>('/tournaments/', d).then(r => r.data)
export const updateTournament = (id: number, d: Partial<Tournament>) => http.patch<Tournament>(`/tournaments/${id}`, d).then(r => r.data)
export const deleteTournament = (id: number) => http.delete(`/tournaments/${id}`)

// ─── Teams ────────────────────────────────────────────────────────────────────
export const getTeams = () => http.get<Team[]>('/teams/').then(r => r.data)
export const createTeam = (d: Omit<Team, 'id'>) => http.post<Team>('/teams/', d).then(r => r.data)
export const updateTeam = (id: number, d: Partial<Team>) => http.patch<Team>(`/teams/${id}`, d).then(r => r.data)
export const deleteTeam = (id: number) => http.delete(`/teams/${id}`)

// ─── Players ──────────────────────────────────────────────────────────────────
export const getPlayers = (teamId?: number) =>
  http.get<Player[]>('/players/', { params: teamId ? { team_id: teamId } : {} }).then(r => r.data)
export const createPlayer = (d: Omit<Player, 'id' | 'team'>) => http.post<Player>('/players/', d).then(r => r.data)
export const updatePlayer = (id: number, d: Partial<Player>) => http.patch<Player>(`/players/${id}`, d).then(r => r.data)
export const deletePlayer = (id: number) => http.delete(`/players/${id}`)

// ─── Matches ──────────────────────────────────────────────────────────────────
export const getMatches = () => http.get<Match[]>('/matches/').then(r => r.data)
export const getMatch = (id: number) => http.get<Match>(`/matches/${id}`).then(r => r.data)
export const createMatch = (d: Omit<Match, 'id' | 'tournament' | 'home_team' | 'away_team' | 'squad'>) =>
  http.post<Match>('/matches/', d).then(r => r.data)
export const updateMatch = (id: number, d: Partial<Match>) => http.patch<Match>(`/matches/${id}`, d).then(r => r.data)
export const deleteMatch = (id: number) => http.delete(`/matches/${id}`)
export const getOfficialSheet = (matchId: number) => http.get<OfficialSheet>(`/matches/${matchId}/official-sheet`).then(r => r.data)
export const getOfficialSheetPdf = (matchId: number) => http.get<Blob>(`/matches/${matchId}/official-sheet/pdf`, { responseType: 'blob' }).then(r => r.data)
export const previewMatchPDF = (matchId: number, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return http.post<MatchPDFPreviewResult>(`/pdf/matches/${matchId}/preview`, form).then(r => r.data)
}
export const confirmMatchPDF = (matchId: number, file: File, confirmation: MatchPDFConfirmation) => {
  const form = new FormData()
  form.append('file', file)
  form.append('confirmation_json', JSON.stringify(confirmation))
  return http.post<MatchPDFConfirmResult>(`/pdf/matches/${matchId}/confirm`, form).then(r => r.data)
}

// ─── Squad ────────────────────────────────────────────────────────────────────
export const getSquad = (matchId: number) => http.get<MatchSquad[]>(`/matches/${matchId}/squad`).then(r => r.data)
export const upsertSquadPlayer = (matchId: number, d: Omit<MatchSquad, 'id' | 'player'>) =>
  http.put<MatchSquad>(`/matches/${matchId}/squad`, d).then(r => r.data)
export const removeSquadPlayer = (matchId: number, playerId: number) =>
  http.delete(`/matches/${matchId}/squad/${playerId}`)

// ─── Events ───────────────────────────────────────────────────────────────────
export const getEvents = (matchId: number) => http.get<Event[]>(`/matches/${matchId}/events`).then(r => r.data)
export const createEvent = (matchId: number, d: Omit<Event, 'id' | 'player' | 'assist_player' | 'goalkeeper' | 'sub_in_player' | 'sub_out_player'>) =>
  http.post<Event>(`/matches/${matchId}/events`, d).then(r => r.data)
export const deleteEvent = (matchId: number, eventId: number) =>
  http.delete(`/matches/${matchId}/events/${eventId}`)
export const deleteLastEvent = (matchId: number) =>
  http.delete<Event>(`/matches/${matchId}/events/last`).then(r => r.data)

// Analytical records are separate from legacy live events and official scores.
export const getAnalysisEvents = (matchId: number) =>
  http.get<AnalysisEvent[]>(`/matches/${matchId}/analysis-events`).then(r => r.data)
export const getReviewedMetrics = (matchId: number) =>
  http.get<ReviewedMetrics>(`/matches/${matchId}/reviewed-metrics`).then(r => r.data)
export const createAnalysisEvent = (matchId: number, data: AnalysisEventInput) =>
  http.post<AnalysisEvent>(`/matches/${matchId}/analysis-events`, data).then(r => r.data)
export const deactivateAnalysisEvent = (eventId: number, reason: string) =>
  http.delete<AnalysisEvent>(`/analysis-events/${eventId}`, { params: { reason } }).then(r => r.data)
export const restoreAnalysisEvent = (eventId: number, reason: string) =>
  http.post<AnalysisEvent>(`/analysis-events/${eventId}/restore`, null, { params: { reason } }).then(r => r.data)
export const getCanonicalEvents = (matchId: number) =>
  http.get<CanonicalEvent[]>(`/matches/${matchId}/canonical-events`).then(r => r.data)
export const getCanonicalState = (matchId: number) =>
  http.get<CanonicalMatchState>(`/matches/${matchId}/canonical-state`).then(r => r.data)
export const getCanonicalMetrics = (matchId: number) =>
  http.get<ReviewedMetrics>(`/matches/${matchId}/canonical-metrics`).then(r => r.data)
export const deactivateCanonicalEvent = (eventId: number, reason: string) =>
  http.delete<CanonicalEvent>(`/canonical-events/${eventId}`, { params: { reason } }).then(r => r.data)
export const deactivateLastCanonicalEvent = (matchId: number, reason: string) =>
  http.delete<CanonicalEvent>(`/matches/${matchId}/canonical-events/last`, { data: { reason } }).then(r => r.data)
export const resetCanonicalAnalysis = (matchId: number, reason: string) =>
  http.post<{ deactivated_events: number; session_reset: boolean }>(`/matches/${matchId}/canonical-analysis/reset`, { reason }).then(r => r.data)
export const getCanonicalReconciliation = (matchId: number) =>
  http.get<{ official: ReviewedMetrics['official']; discrepancies: ReviewedMetrics['reconciliation']; discipline: ReviewedMetrics['discipline'] }>(`/matches/${matchId}/canonical-reconciliation`).then(r => ({ official: r.data.official, reconciliation: r.data.discrepancies, discipline: r.data.discipline ?? [] }))
export const getWarningsSummary = (matchId: number) =>
  http.get<WarningsSummary>(`/matches/${matchId}/warnings-summary`).then(r => r.data)
export const enableCanonicalAnalysis = (matchId: number) =>
  http.put<{ match_id: number; canonical_analysis_enabled: boolean; reason: string }>(`/matches/${matchId}/canonical-cutover`, { enabled: true, reason: 'analysis preparation started' }).then(r => r.data)
export const createCanonicalEvent = (matchId: number, data: CanonicalEventCommand) =>
  http.post<CanonicalEvent>(`/matches/${matchId}/canonical-events`, data).then(r => r.data)
export const reviseCanonicalEvent = (eventId: number, data: CanonicalEventRevisionInput) =>
  http.patch<CanonicalEvent>(`/canonical-events/${eventId}`, data).then(r => r.data)
export const getCanonicalPlayerProjection = (matchId: number, params: { player_id: number; team_id?: number; period?: number; from_regulation_seconds?: number; to_regulation_seconds?: number }) =>
  http.get<CanonicalPlayerProjection>(`/matches/${matchId}/canonical-player-projection`, { params }).then(r => r.data)
export const getAnalysisSession = (matchId: number) =>
  http.get<AnalysisSession>(`/matches/${matchId}/analysis-session`).then(r => r.data)
export const saveAnalysisSession = (matchId: number, data: AnalysisSessionUpdate) =>
  http.put<AnalysisSession>(`/matches/${matchId}/analysis-session`, data).then(r => r.data)
export const createReportPackage = (matchId: number, data: ReportPackageInput) =>
  http.post<ReviewedReportPackage>(`/matches/${matchId}/report-packages`, data).then(r => r.data)
export const approveReportPackage = (packageId: number) =>
  http.post<ReviewedReportPackage>(`/report-packages/${packageId}/approve`).then(r => r.data)
export const getPublicationStatus = (packageId: number) =>
  http.get<ReportPublicationStatus>(`/report-packages/${packageId}/publication-status`).then(r => r.data)
export const attestRecoveryArtifact = (packageId: number, artifactType: 'postgres_dump' | 'imported_pdf_export', location: string) =>
  http.put(`/report-packages/${packageId}/recovery-artifacts/${artifactType}`, { location }).then(r => r.data)
export const publishReportPackage = (packageId: number) =>
  http.post<ReportPublicationStatus>(`/report-packages/${packageId}/publish`).then(r => r.data)

// ─── Goalkeeper shots ─────────────────────────────────────────────────────────
export const createGoalkeeperShot = (matchId: number, d: Partial<GoalkeeperShotCreate>) =>
  http.post<GoalkeeperShot>(`/matches/${matchId}/goalkeeper-shots`, d).then(r => r.data)
export const listGoalkeeperShots = (matchId: number) =>
  http.get<GoalkeeperShot[]>(`/matches/${matchId}/goalkeeper-shots`).then(r => r.data)
export const deleteGoalkeeperShot = (matchId: number, shotId: number) =>
  http.delete(`/matches/${matchId}/goalkeeper-shots/${shotId}`)

// ─── Clips ────────────────────────────────────────────────────────────────────
export const getClips = (matchId: number) => http.get<Clip[]>(`/matches/${matchId}/clips`).then(r => r.data)
export const createClip = (matchId: number, d: Omit<Clip, 'id'>) =>
  http.post<Clip>(`/matches/${matchId}/clips`, d).then(r => r.data)
export const updateClip = (matchId: number, clipId: number, d: Partial<Clip>) =>
  http.patch<Clip>(`/matches/${matchId}/clips/${clipId}`, d).then(r => r.data)
export const deleteClip = (matchId: number, clipId: number) =>
  http.delete(`/matches/${matchId}/clips/${clipId}`)

// ─── PDF ──────────────────────────────────────────────────────────────────────
export const importPDF = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return http.post<Match>('/pdf/import', form).then(r => r.data)
}
export const parsePDF = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return http.post<PDFPreview>('/pdf/parse', form).then(r => r.data)
}
export const confirmPDF = (file: File, confirmation: PDFImportConfirmation) => {
  const form = new FormData()
  form.append('file', file)
  form.append('confirmation_json', JSON.stringify(confirmation))
  return http.post<PDFImportResult>('/pdf/confirm', form).then(r => r.data)
}

export const getFixtures = (status?: 'pending' | 'all') =>
  http.get<ScheduledFixture[]>('/pdf/fixtures', { params: status ? { status } : {} }).then(r => r.data)
// This endpoint returns confirmed fixtures with stable stage metadata for grouping.
export const getPreloadedFixtures = () => http.get<ScheduledFixture[]>('/pdf/fixtures').then(r => r.data)
export const getPreloadedFixture = (fixtureKey: string) => http.get<ScheduledFixture>(`/pdf/fixtures/${fixtureKey}`).then(r => r.data)
export const getFixtureRoster = (fixtureKey: string) => http.get<FixtureRoster>(`/pdf/fixtures/${fixtureKey}/roster`).then(r => r.data)
export const resolveFixtureRoster = (fixtureKey: string, resolutions: FixtureRosterResolution[]) =>
  http.post(`/pdf/fixtures/${fixtureKey}/roster-resolution`, { resolutions }).then(r => r.data)
export const previewFixturePDF = (fixtureKey: string, file: File) => {
  const form = new FormData()
  form.append('fixture_key', fixtureKey)
  form.append('file', file)
  return http.post<FixturePreviewResult>('/pdf/fixture-preview', form).then(r => r.data)
}
export const confirmFixturePDF = (fixtureKey: string, file: File, confirmation: FixtureConfirmation) => {
  const form = new FormData()
  form.append('fixture_key', fixtureKey)
  form.append('file', file)
  form.append('confirmation_json', JSON.stringify(confirmation))
  return http.post<FixtureConfirmResult>('/pdf/fixture-confirm', form).then(r => r.data)
}

// ─── Fixture Review Flow ──────────────────────────────────────────────────────
export const reviewFixturePDF = (fixtureKey: string) =>
  http.get<FixturePreviewResult>(`/pdf/fixtures/${fixtureKey}/review`).then(r => r.data)

export const confirmFixtureReview = (fixtureKey: string, confirmation: FixtureConfirmation) =>
  http.post<FixtureConfirmResult>(`/pdf/fixtures/${fixtureKey}/review`, confirmation).then(r => r.data)
