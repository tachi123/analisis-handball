import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import MatchLive from './MatchLive'
import GoalkeeperMode from './GoalkeeperMode'

const api = vi.hoisted(() => ({ getMatch: vi.fn(), getCanonicalEvents: vi.fn(), getCanonicalState: vi.fn(), createCanonicalEvent: vi.fn() }))
vi.mock('../api/client', () => api)

describe('legacy capture routes', () => {
  it('redirects goalkeeper capture to canonical analysis without legacy writers', () => {
    render(<MemoryRouter initialEntries={['/match/7/goalkeeper']}><Routes><Route path="/match/:matchId/goalkeeper" element={<GoalkeeperMode />} /><Route path="/match/:matchId/analysis" element={<p>Canonical analysis</p>} /></Routes></MemoryRouter>)
    expect(screen.getByText('Canonical analysis')).toBeTruthy()
  })

  it('keeps the live bookmark on the canonical capture component', async () => {
    api.getMatch.mockResolvedValue({ id: 7, home_team: { id: 1, name: 'SAPA' }, away_team: { id: 2, name: 'Rival' }, home_score: 0, away_score: 0, squad: [] })
    api.getCanonicalEvents.mockResolvedValue([])
    api.getCanonicalState.mockResolvedValue({ analytical_score: {}, possession: null, active_goalkeepers: {}, player_states: {}, discipline: [] })
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/match/7/live']}><Routes><Route path="/match/:matchId/live" element={<MatchLive />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByText('Nueva observación canónica')).toBeTruthy()
  })
})
