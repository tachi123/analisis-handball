import { describe, expect, it } from 'vitest'
import { decodePublicReport } from './projection'

const publicReport = { schema_version: 'public-report-v1', report_version: 1, match: { date: '2026-08-22', home_team: 'SAPA', away_team: 'Banfield' }, source: { label: 'Broadcast', status: 'public_reference' }, coaching: { question: 'How do we defend?', pattern_statement: 'Close the lane.', action: { kind: 'change', text: 'Close earlier.' } }, metrics: { defensive_action: { count: 3, denominator: 'not_applicable' } }, reconciliation: [], uncertainty_disclosure: 'One clock is unverified.', evidence: [{ reference: 'Sequence 1', period: 1, regulation_seconds: 120, clock_unverified: false, observation: 'Lane open.', media_available: false }] }

const publicReportWithPlayers = {
  schema_version: 'public-report-v1', report_version: 1,
  match: { date: '2026-08-22', home_team: 'SAPA', away_team: 'Banfield' },
  source: { label: 'Broadcast', status: 'public_reference' },
  coaching: { question: 'How do we defend?', pattern_statement: 'Close the lane.', action: { kind: 'change', text: 'Close earlier.' } },
  metrics: { defensive_action: { count: 3, denominator: 'not_applicable' }, 'shot_conversion': { count: 5, denominator: 20 } },
  players: [
    { slug: 'john-doe', name: 'John Doe', jersey_number: '10', team_side: 'home', role: 'field_player', metrics: { shot_conversion: 0.25, defensive_action: 3 }, evidence: [{ reference: 'Sequence 1', period: 1 }] },
    { slug: 'jane-smith', name: 'Jane Smith', jersey_number: '7', team_side: 'home', role: 'field_player', metrics: { shot_conversion: 0.18, defensive_action: 2 }, evidence: [{ reference: 'Sequence 2', period: 2 }] },
    { slug: 'gk-1', name: 'Goalkeeper', jersey_number: '1', team_side: 'home', role: 'goalkeeper', metrics: { saves: 7, save_rate: 0.75, goals_conceded: 2, shots_faced: 20 }, evidence: [{ reference: 'Sequence 3', period: 1 }] },
  ],
  reconciliation: [], uncertainty_disclosure: 'One clock is unverified.', evidence: [{ reference: 'Sequence 1', period: 1, regulation_seconds: 120, clock_unverified: false, observation: 'Lane open.', media_available: false }]
}

const publicReportWithPlayersNoEvidence = {
  schema_version: 'public-report-v1', report_version: 1,
  match: { date: '2026-08-22', home_team: 'SAPA', away_team: 'Banfield' },
  source: { label: 'Broadcast', status: 'public_reference' },
  coaching: { question: 'How do we defend?', pattern_statement: 'Close the lane.', action: { kind: 'change', text: 'Close earlier.' } },
  metrics: { defensive_action: { count: 3, denominator: 'not_applicable' }, 'shot_conversion': { count: 5, denominator: 20 } },
  players: [
    { slug: 'john-doe', name: 'John Doe', jersey_number: '10', team_side: 'home', role: 'field_player', metrics: { shot_conversion: 0.25 }, evidence: [] },
  ],
  reconciliation: [], uncertainty_disclosure: 'One clock is unverified.', evidence: [{ reference: 'Sequence 1', period: 1, regulation_seconds: 120, clock_unverified: false, observation: 'Lane open.', media_available: false }]
}

describe('public report projection', () => {
  it('accepts only the public-report-v1 allowlist', () => expect(decodePublicReport(publicReport)).toMatchObject({ schema_version: 'public-report-v1', evidence: [{ reference: 'Sequence 1' }] }))
  it('accepts absent players (legacy reports backward-compatible)', () => {
    // Legacy reports without players should work fine
    const result = decodePublicReport(publicReport)
    expect(result.players).toBeNull()
  })
  it('accepts reports with players from the explicit players contract', () => {
    const result = decodePublicReport(publicReportWithPlayers)
    expect(result.players).toBeDefined()
    expect(result.players!.length).toBe(3)
    expect(result.players![0].slug).toBe('john-doe')
    expect(result.players![0].name).toBe('John Doe')
    expect(result.players![0].team_side).toBe('home')
    expect(result.players![0].role).toBe('field_player')
    expect(result.players![0].metrics.shot_conversion).toBe(0.25)
    expect(result.players![0].evidence.length).toBe(1)
    expect(result.players![1].slug).toBe('jane-smith')
    expect(result.players![1].name).toBe('Jane Smith')
    expect(result.players![1].team_side).toBe('home')
    expect(result.players![1].role).toBe('field_player')
    expect(result.players![1].metrics.shot_conversion).toBe(0.18)
    expect(result.players![1].evidence.length).toBe(1)
    expect(result.players![2].slug).toBe('gk-1')
    expect(result.players![2].name).toBe('Goalkeeper')
    expect(result.players![2].team_side).toBe('home')
    expect(result.players![2].role).toBe('goalkeeper')
    expect(Object.keys(result.players![2].metrics)).toEqual(['saves', 'save_rate', 'goals_conceded', 'shots_faced'])
  })
  it('rejects player with invalid slug (must be lowercase alphanumeric/hyphens)', () => {
    expect(() => decodePublicReport({
      ...publicReportWithPlayers, players: [
        { slug: 'John Doe', name: 'John Doe', jersey_number: '10', team_side: 'home', role: 'field_player', metrics: { shot_conversion: 0.25 }, evidence: [] },
      ]
    })).toThrow('Player slug must be a safe public slug')
  })
  it('rejects player with invalid team_side', () => {
    expect(() => decodePublicReport({
      ...publicReportWithPlayers, players: [
        { slug: 'john-doe', name: 'John Doe', jersey_number: '10', team_side: 'neutral', role: 'field_player', metrics: { shot_conversion: 0.25 }, evidence: [] },
      ]
    })).toThrow('Player team_side must be "home" or "away"')
  })
  it('rejects player with private fields in metrics', () => {
    expect(() => decodePublicReport({
      ...publicReportWithPlayers, players: [
        { slug: 'john-doe', name: 'John Doe', jersey_number: '10', team_side: 'home', role: 'field_player', metrics: { shot_conversion: 0.25, private_note: 'secret' }, evidence: [] },
      ]
    })).toThrow('The public report contains a restricted field')
  })
  it('accepts report with players and no evidence per player', () => {
    const result = decodePublicReport(publicReportWithPlayersNoEvidence)
    expect(result.players![0].evidence).toHaveLength(0)
  })
  it('rejects player with missing role', () => {
    expect(() => decodePublicReport({
      ...publicReportWithPlayers, players: [
        { slug: 'john-doe', name: 'John Doe', jersey_number: '10', team_side: 'home', metrics: { shot_conversion: 0.25 }, evidence: [] },
      ]
    })).toThrow('Player role is required and must be "goalkeeper" or "field_player".')
  })
  it('rejects player with invalid role value', () => {
    expect(() => decodePublicReport({
      ...publicReportWithPlayers, players: [
        { slug: 'john-doe', name: 'John Doe', jersey_number: '10', team_side: 'home', role: 'goalie', metrics: { shot_conversion: 0.25 }, evidence: [] },
      ]
    })).toThrow('Player role must be "goalkeeper" or "field_player".')
  })
  it('accepts report with players absent (legacy)', () => {
    const result = decodePublicReport(publicReport)
    expect(result.players).toBeNull()
  })
})