import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import GoalkeeperPanel from './GoalkeeperPanel'

const api = vi.hoisted(() => ({ getMatch: vi.fn(), getAnalysisSession: vi.fn(), getCanonicalPlayerProjection: vi.fn() }))
const youtube = vi.hoisted(() => ({ seekTo: vi.fn() }))
vi.mock('../api/client', () => api)
vi.mock('../hooks/useYouTubeSync', () => ({ useYouTubeSync: () => ({ availability: 'ready', seekTo: youtube.seekTo, playerRef: { current: null } }) }))

describe('GoalkeeperPanel', () => {
  it('renders server metrics and separates unknown keeper coverage', async () => {
    api.getMatch.mockResolvedValue({ id: 1, squad: [{ player_id: 20, jersey_number: 1, is_goalkeeper: true, player: { name: 'GK' } }] })
    api.getAnalysisSession.mockResolvedValue(null)
    api.getCanonicalPlayerProjection.mockResolvedValue({ player: { id: 20, name: 'GK', team_id: 2, roster_source: 'match_squad' }, filters: {}, participation: { on: 0, off: 0, substitution: 0, evidence: [] }, metrics: { saves: 2, goals_conceded: 1, save_rate: { numerator: 2, denominator: 3, value: .6667 } }, discipline: { yellow: 0, two_minute: 0, red: 0, evidence: [] }, shot_map: { zones: { '1': 1 }, recorded: 1, missing_zone: 0, goalkeeper_unknown: 2, excluded: 0, unknown: 0, clock_unverified: 1 }, evidence: [], unfiltered_context: { canonical_metrics: { metrics: {} }, reconciliation: { discrepancies: [] } } })
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/match/1/goalkeeper-panel']}><Routes><Route path="/match/:matchId/goalkeeper-panel" element={<GoalkeeperPanel />} /></Routes></MemoryRouter></QueryClientProvider>)
    await screen.findByText('Atajadas')
    expect(screen.getByText('Goles recibidos')).not.toBeNull()
    expect(screen.getByText(/tiros sin arquero activo observado/i)).not.toBeNull()
    fireEvent.change(screen.getByLabelText('Filtrar período'), { target: { value: '2' } })
    await waitFor(() => expect(api.getCanonicalPlayerProjection).toHaveBeenLastCalledWith(1, expect.objectContaining({ player_id: 20, period: 2 })))
  })

  it('renders projection evidence IDs and seeks an anchored evidence item', async () => {
    api.getMatch.mockResolvedValue({ id: 1, squad: [{ player_id: 20, jersey_number: 1, is_goalkeeper: true, player: { name: 'GK' } }] })
    api.getAnalysisSession.mockResolvedValue({ source: { id: 1 }, time_segments: [] })
    api.getCanonicalPlayerProjection.mockResolvedValue({ player: { id: 20, name: 'GK', team_id: 2, roster_source: 'match_squad' }, filters: {}, participation: { on: 0, off: 0, substitution: 0, evidence: [] }, metrics: { saves: 0, goals_conceded: 0, save_rate: null }, discipline: { yellow: 0, two_minute: 0, red: 0, evidence: [] }, shot_map: { zones: {}, recorded: 0, missing_zone: 0, goalkeeper_unknown: 0, excluded: 0, unknown: 0, clock_unverified: 1 }, evidence: [{ id: 77, revision: 3, sequence: 7, period: 1, regulation_seconds: null, clock_unverified: true, bucket: 'clock_unverified', payload: { kind: 'shot' }, evidence: [{ id: 9, kind: 'video', video_anchor_seconds: 50 }] }], unfiltered_context: { canonical_metrics: { metrics: {} }, reconciliation: { discrepancies: [] } } })
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/match/1/goalkeeper-panel']}><Routes><Route path="/match/:matchId/goalkeeper-panel" element={<GoalkeeperPanel />} /></Routes></MemoryRouter></QueryClientProvider>)

    fireEvent.click(await screen.findByRole('button', { name: /evento #7/i }))
    expect(youtube.seekTo).toHaveBeenCalledWith(48)
    expect(screen.getByText(/evento 77; revisión 3/i)).not.toBeNull()
  })
})
