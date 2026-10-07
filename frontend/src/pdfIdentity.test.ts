import { describe, expect, it } from 'vitest'
import { hasRosterContext, namedTeams, normalizeIdentityName, playerCandidates } from './pdfIdentity'
import type { PDFPlayerPreview, PDFTeamPreview, Player, Team } from './types'

const team: Team = { id: 1, name: 'SAPA', club_name: null, category: null }
const previewTeam: PDFTeamPreview = { name: 'SAPA', players: [{ number: 7, name: 'Ana Gómez', goals: 0, yellow: 0, two_min: 0, red: 0, blue: 0 }] }
const player: Player = { id: 1, name: 'Ana Gomez', default_jersey_number: 7, global_position: null, team_id: 1, team }

describe('PDF identity candidates', () => {
  it('normalizes names but requires team and jersey roster context', () => {
    expect(normalizeIdentityName(' Ana Gómez ')).toBe('ana gomez')
    expect(namedTeams(previewTeam, [team])).toEqual([team])
    expect(hasRosterContext(team, previewTeam, [player])).toBe(true)
    expect(playerCandidates(previewTeam.players[0], 1, [player])).toEqual([player])
    expect(playerCandidates(previewTeam.players[0], null, [player])).toEqual([])
  })

  it('keeps duplicate player names ambiguous', () => {
    const duplicate: Player = { ...player, id: 2 }
    const previewPlayer: PDFPlayerPreview = previewTeam.players[0]

    expect(playerCandidates(previewPlayer, 1, [player, duplicate])).toHaveLength(2)
  })

  it('proposes a reusable team only with matching roster context', () => {
    expect(hasRosterContext(team, previewTeam, [player])).toBe(true)
    expect(hasRosterContext(team, previewTeam, [{ ...player, default_jersey_number: 9 }])).toBe(false)
  })
})
