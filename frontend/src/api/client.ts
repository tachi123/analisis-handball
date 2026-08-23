import axios from 'axios'
import type {
import type { GoalkeeperShot, GoalkeeperShotCreate } from '../types'
  Tournament, Team, Player, Match, MatchSquad, Event, Clip,
  TokenResponse, UserRead,
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
  return http.post('/pdf/parse', form).then(r => r.data)
}

// ─── Goalkeeper shots ─────────────────────────────────────────────────────────
export const createGoalkeeperShot = (matchId: number, d: Partial<GoalkeeperShotCreate>) =>
  http.post<GoalkeeperShot>(`/matches/${matchId}/goalkeeper-shots`, d).then(r => r.data)
export const listGoalkeeperShots = (matchId: number) =>
  http.get<GoalkeeperShot[]>(`/matches/${matchId}/goalkeeper-shots`).then(r => r.data)
export const deleteGoalkeeperShot = (matchId: number, shotId: number) =>
  http.delete(`/matches/${matchId}/goalkeeper-shots/${shotId}`)
