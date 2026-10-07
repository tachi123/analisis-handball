import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CanonicalEvent } from '../types'

const api = vi.hoisted(() => ({ getMatch: vi.fn(), getCanonicalEvents: vi.fn(), getCanonicalState: vi.fn(), getCanonicalMetrics: vi.fn(), getCanonicalReconciliation: vi.fn(), getAnalysisSession: vi.fn() }))
const seekTo = vi.hoisted(() => vi.fn())
const playerState = vi.hoisted(() => ({ availability: 'ready' }))
vi.mock('../api/client', () => api)
vi.mock('../hooks/useYouTubeSync', () => ({ useYouTubeSync: () => ({ playerRef: { current: null }, availability: playerState.availability, seekTo }) }))
import MatchReportsTimeline from './MatchReportsTimeline'

const anchored: CanonicalEvent = { id: 1, sequence: 1, active: true, payload: { kind: 'shot', period: 1, regulation_seconds: 20, clock_unverified: false, team_id: 1, player_id: 9, outcome: 'goal', fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null }, evidence: [{ id: 1, kind: 'video', video_anchor_seconds: 12, uncertainty: [] }] }
const noAnchor: CanonicalEvent = { ...anchored, id: 2, sequence: 2, evidence: [], payload: { ...anchored.payload, kind: 'turnover', player_id: null, regulation_seconds: null, clock_unverified: true, evidence_state: 'ambiguous' } }

function renderPage(path = '/match/1/timeline') { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><Routes><Route path="/match/:matchId/timeline" element={<MatchReportsTimeline />} /></Routes></MemoryRouter></QueryClientProvider>) }

describe('MatchReportsTimeline', () => {
  beforeEach(() => {
    api.getMatch.mockResolvedValue({ id: 1, home_team: { name: 'Local' }, away_team: { name: 'Visitante' }, squad: [{ player_id: 9, jersey_number: 9, player: { name: 'Ana' } }] })
    api.getCanonicalEvents.mockResolvedValue([anchored, noAnchor])
    api.getCanonicalState.mockResolvedValue({ analytical_score: { '1': 1 }, possession: null, active_goalkeepers: {}, player_states: {}, discipline: [] })
    api.getCanonicalMetrics.mockResolvedValue({ metrics: { shots: { name: 'shots', count: 2, numerator: 1, denominator: 2, excluded: 0, unknown: 0, clock_unverified: 1 } }, eligibility: { eligible: 2, excluded: 0, unknown: 0, unresolved: 0, clock_unverified: 1 } })
    api.getCanonicalReconciliation.mockResolvedValue({ official: { snapshot_id: 'pdf-1', home_score: 1, away_score: 0 }, reconciliation: [], discipline: [] })
    api.getAnalysisSession.mockResolvedValue({ source: { id: 1, original_url: 'https://youtube.test', provider: 'youtube', provider_video_id: 'abc', availability_state: 'ready' }, video_position_seconds: 0, time_segments: [] })
    playerState.availability = 'ready'
    seekTo.mockClear()
  })

  it('loads canonical reads, seeks only a usable anchor, and keeps the server context unfiltered', async () => {
    renderPage()
    const anchoredButton = await screen.findByRole('button', { name: /#1/ })
    fireEvent.click(anchoredButton)
    expect(seekTo).toHaveBeenCalledWith(10)
    fireEvent.change(screen.getByLabelText('Filtrar por estado de evidencia'), { target: { value: 'ambiguous' } })
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('1 eventos visibles'))
    expect(screen.getByLabelText('Contexto canónico sin filtrar').textContent).toContain('Conteo: 2')
    expect(screen.queryByRole('button', { name: /guardar|revisar evidencia|excluir/i })).toBeNull()
  })

  it('selects an unanchored event without moving playback and explains why', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /#2/ }))
    expect(seekTo).not.toHaveBeenCalled()
    expect(screen.getByRole('status').textContent).toContain('no tiene un ancla utilizable')
  })

  it('keeps details usable when the player is unavailable and explains the no-seek result', async () => {
    playerState.availability = 'unavailable'
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /#1/ }))
    expect(seekTo).not.toHaveBeenCalled()
    expect(screen.getByRole('status').textContent).toContain('el reproductor no está disponible')
  })

  it('shows the established unavailable state when the match cannot be loaded', async () => {
    api.getMatch.mockRejectedValueOnce(new Error('403'))
    renderPage()
    expect((await screen.findByRole('alert')).textContent).toContain('No se pudo cargar el partido: 403')
  })
})
