import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { userEvent } from '@vitest/browser/context'
import { act } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import WarningsPanel from './WarningsPanel'
import type { WarningsSummary } from '../types'

const api = vi.hoisted(() => ({ getCanonicalEvents: vi.fn(), getAnalysisSession: vi.fn() }))
vi.mock('../api/client', () => api)

const comparison = (overrides = {}) => ({ canonical: 2, official: 1, status: 'missing_in_official' as const, tolerance: 0 as const, canonical_event_ids: [9], evidence_ids: [4], ...overrides })
const summary: WarningsSummary = {
  match_id: 1, official_snapshot_id: 'snapshot-1',
  players: [{ player: { id: 7, name: 'Ana', jersey_number: 8, side: 'home' }, metrics: { goals: comparison(), yellow: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), two_minute: comparison({ canonical: null, official: 1, status: 'missing_in_canonical', canonical_event_ids: [] }), red: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), blue: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }) } }],
  match_totals: { metrics: { goals: comparison(), yellow: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), two_minute: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), red: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }), blue: comparison({ canonical: 0, official: 0, status: 'exact', canonical_event_ids: [] }) } },
  limitations: [],
}
const event = { id: 9, sequence: 3, active: true, payload: { kind: 'shot' as const, period: 1, regulation_seconds: 20, clock_unverified: true, team_id: 1, player_id: 7, outcome: 'goal', fact_kind: 'observed' as const, evidence_state: 'confirmed' as const, uncertainty: [], note: null }, evidence: [{ id: 4, kind: 'video' as const, video_anchor_seconds: 42, uncertainty: [] }] }

function renderPanel() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><WarningsPanel matchId={1} summary={summary} /></QueryClientProvider>)
}

describe('WarningsPanel native disclosure', () => {
  afterEach(() => vi.clearAllMocks())

  it('expands with Enter and collapses with Space through Chromium native button behavior', async () => {
    api.getCanonicalEvents.mockResolvedValue([event])
    api.getAnalysisSession.mockResolvedValue({ source: null, video_position_seconds: 0, time_segments: [] })
    renderPanel()

    const button = screen.getAllByRole('button', { name: /2 \/ 1/ })[0]
    const detailId = button.getAttribute('aria-controls')!
    button.focus()

    await act(() => userEvent.keyboard('{Enter}'))
    expect(button.getAttribute('aria-expanded')).toBe('true')
    expect((await screen.findByLabelText('Detalle de total-goals')).getAttribute('id')).toBe(detailId)

    await act(() => userEvent.keyboard('{Space}'))
    await waitFor(() => expect(button.getAttribute('aria-expanded')).toBe('false'))
    expect(screen.queryByLabelText('Detalle de total-goals')).toBeNull()
  })
})
