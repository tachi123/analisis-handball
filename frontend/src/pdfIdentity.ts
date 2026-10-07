import type { PDFPlayerPreview, PDFTeamPreview, Player, Team } from './types'

export const normalizeIdentityName = (name: string) =>
  name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().replace(/\s+/g, ' ').toLowerCase()

export const namedTeams = (previewTeam: PDFTeamPreview, teams: Team[]) =>
  teams.filter((team) => normalizeIdentityName(team.name) === normalizeIdentityName(previewTeam.name))

export const hasRosterContext = (team: Team, previewTeam: PDFTeamPreview, players: Player[]) =>
  previewTeam.players.some((previewPlayer) => players.some((player) =>
    player.team_id === team.id &&
    player.default_jersey_number === previewPlayer.number &&
    normalizeIdentityName(player.name) === normalizeIdentityName(previewPlayer.name),
  ))

export const playerCandidates = (previewPlayer: PDFPlayerPreview, teamId: number | null, players: Player[]) =>
  teamId === null ? [] : players.filter((player) =>
    player.team_id === teamId &&
    player.default_jersey_number === previewPlayer.number &&
    normalizeIdentityName(player.name) === normalizeIdentityName(previewPlayer.name),
  )
