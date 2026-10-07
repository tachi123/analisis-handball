import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import WarningsPanel from './WarningsPanel'
import type { VideoAvailabilityState, VideoSource, WarningsSummary } from '../types'

const api = vi.hoisted(() => ({ getCanonicalEvents: vi.fn(), getAnalysisSession: vi.fn() }))
const player = vi.hoisted(() => ({ availability: null as VideoAvailabilityState | null, seekTo: vi.fn() }))
vi.mock('../api/client', () => api)
vi.mock('../hooks/useYouTubeSync', async importOriginal => {
  const actual = await importOriginal<typeof import('../hooks/useYouTubeSync')>()
  return { ...actual, useYouTubeSync: (source: VideoSource | null, initialTime?: number) => player.availability ? { playerRef: { current: document.createElement('div') }, currentTime: 0, isPlaying: false, availability: player.availability, seekTo: player.seekTo, play: vi.fn(), pause: vi.fn(), pauseAndReadCurrentTime: vi.fn() } : actual.useYouTubeSync(source, initialTime) }
})

const comparison = (overrides = {}) => ({ canonical: 2, official: 1, status: 'missing_in_official' as const, tolerance: 0 as const, canonical_event_ids: [9], evidence_ids: [4], ...overrides })
const summary: WarningsSummary = {
  match_id: 1, official_snapshot_id: 'snapshot-1',
  players: [{ player: { id: 7, name: 'Ana', jersey_number: 8, side: 'home' }, metrics: { goals: comparison(), yellow: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), two_minute: comparison({ canonical: null, official: 1, status: 'missing_in_canonical', canonical_event_ids: [] }), red: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), blue: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }) } }],
  match_totals: { metrics: { goals: comparison(), yellow: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), two_minute: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), red: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), blue: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }) } },
  limitations: [{ check: 'goal_timestamps', status: 'not_comparable', reason: 'No timestamps' }, { check: 'card_timestamps', status: 'not_comparable', reason: 'No timestamps' }, { check: 'goalkeeper_substitutions', status: 'not_comparable', reason: 'No substitutions' }],
}
const event = { id: 9, sequence: 3, active: true, payload: { kind: 'shot' as const, period: 1, regulation_seconds: 20, clock_unverified: true, team_id: 1, player_id: 7, outcome: 'goal', fact_kind: 'observed' as const, evidence_state: 'confirmed' as const, uncertainty: [], note: null }, evidence: [{ id: 4, kind: 'video' as const, video_anchor_seconds: 42, uncertainty: [] }] }
const unrelated = { ...event, id: 10, sequence: 4, payload: { ...event.payload, kind: 'turnover' as const } }

function renderPanel() { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><WarningsPanel matchId={1} summary={summary} /></QueryClientProvider>) }

describe('WarningsPanel', () => {
  afterEach(() => { cleanup(); player.availability = null; vi.clearAllMocks() })

  it('expands and collapses a linked comparison with native button ARIA and live notices', async () => {
    api.getCanonicalEvents.mockResolvedValue([event, unrelated]); api.getAnalysisSession.mockResolvedValue({ source: null, video_position_seconds: 0, time_segments: [] })
    renderPanel()
    const button = screen.getAllByRole('button', { name: /2 \/ 1/ })[0]
    expect(button.tagName).toBe('BUTTON')
    expect(button.getAttribute('aria-expanded')).toBe('false')
    const detailId = button.getAttribute('aria-controls')!
    fireEvent.click(button)
    expect(button.getAttribute('aria-expanded')).toBe('true')
    expect((await screen.findByLabelText('Detalle de total-goals')).getAttribute('id')).toBe(detailId)
    expect(screen.getByRole('status').textContent).toContain('expandido')
    expect(await screen.findByText('Evento #3')).toBeTruthy()
    expect(screen.queryByText('Evento #4')).toBeNull()
    fireEvent.click(button)
    expect(button.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByLabelText('Detalle de total-goals')).toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(button))
    expect(screen.getByRole('status').textContent).toContain('contraído')
  })

  it('states that comparisons without event IDs cannot be expanded', () => {
    renderPanel()
    const message = screen.getAllByText('No hay eventos canónicos vinculados.')[0]
    expect(message.closest('div')?.querySelector('button')).toBeNull()
  })

  it('shows the required event fields and PDF evidence without a seek action', async () => {
    api.getCanonicalEvents.mockResolvedValue([{ ...event, evidence: [{ id: 4, kind: 'pdf', uncertainty: [] }] }]); api.getAnalysisSession.mockResolvedValue({ source: null, video_position_seconds: 0, time_segments: [] })
    renderPanel()
    fireEvent.click(screen.getAllByRole('button', { name: /2 \/ 1/ })[0])
    const linked = await screen.findByLabelText('Eventos canónicos vinculados')
    expect(linked.textContent).toContain('Jugador: #8 Ana')
    expect(linked.textContent).toContain('Tipo: shot')
    expect(linked.textContent).toContain('Período: 1')
    expect(linked.textContent).toContain('Tiempo reglamentario: 20 s')
    expect(linked.textContent).toContain('clock_unverified: sí')
    expect(linked.textContent).toContain('Tiempo de video: sin ancla')
    expect(linked.textContent).toContain('Tipos de evidencia: pdf')
    expect(screen.queryByRole('button', { name: /Ver evidencia de video/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /guardar|revisar|resolver/i })).toBeNull()
  })

  it('selects a video event and seeks only after the player is ready', async () => {
    player.availability = 'ready'
    api.getCanonicalEvents.mockResolvedValue([event])
    api.getAnalysisSession.mockResolvedValue({ source: { id: 1, original_url: 'https://youtube.com/watch?v=abcdefghijk', provider: 'youtube', provider_video_id: 'abcdefghijk', availability_state: 'ready' }, video_position_seconds: 0, time_segments: [] })
    renderPanel()
    fireEvent.click(screen.getAllByRole('button', { name: /2 \/ 1/ })[0])
    const seek = await screen.findByRole('button', { name: 'Ver evidencia de video' })
    fireEvent.click(seek)
    await waitFor(() => expect(player.seekTo).toHaveBeenCalledWith(40))
    expect(screen.getByRole('status').textContent).toContain('Video movido')
  })

  it('keeps unavailable video evidence readable and does not seek', async () => {
    player.availability = 'unavailable'
    api.getCanonicalEvents.mockResolvedValue([event]); api.getAnalysisSession.mockResolvedValue({ source: { id: 1, original_url: 'https://youtube.com/watch?v=abcdefghijk', provider: 'youtube', provider_video_id: 'abcdefghijk', availability_state: 'unavailable' }, video_position_seconds: 0, time_segments: [] })
    renderPanel()
    fireEvent.click(screen.getAllByRole('button', { name: /2 \/ 1/ })[0])
    expect(await screen.findByText(/No hay reproducción disponible/)).toBeTruthy()
    fireEvent.click(await screen.findByRole('button', { name: 'Ver evidencia de video' }))
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('video no está disponible'))
    expect(player.seekTo).not.toHaveBeenCalled()
  })
})
