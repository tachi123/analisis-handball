import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FixturePreparationPage from './FixturePreparationPage'

const api = vi.hoisted(() => ({ enableCanonicalAnalysis: vi.fn(), getPreloadedFixture: vi.fn(), getOfficialSheet: vi.fn(), getOfficialSheetPdf: vi.fn(), saveAnalysisSession: vi.fn() }))
vi.mock('../api/client', () => api)

describe('FixturePreparationPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows imported facts before explicitly starting the selected profile', async () => {
    api.getPreloadedFixture.mockResolvedValue({ linked_match_id: 16, stage: { name: 'Apertura' }, scheduled_date: '2026-04-12', venue: null, unresolved_roster_players: 2 })
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Ci.De.Co. B', score: 41, players: [{ jersey_number: 7, name: 'Sin resolver', official_goals: 3, official_yellow: 0, official_2min: 0, official_red: 0 }] }, away: { name: 'S.A.P.A.', score: 22, players: [] }, provenance: { filename: 'sheet.pdf', page_count: 1 }, pdf_available: false })
    api.enableCanonicalAnalysis.mockResolvedValue({ canonical_analysis_enabled: true })
    api.saveAnalysisSession.mockResolvedValue({})
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/fixtures/fixture-16']}><Routes><Route path="/fixtures/:fixtureKey" element={<FixturePreparationPage />} /><Route path="/match/:matchId/review" element={<p>review</p>} /></Routes></MemoryRouter></QueryClientProvider>)

    expect(await screen.findByText('Contexto oficial')).toBeTruthy()
    expect(screen.getByText('Ci.De.Co. B 41 - 22 S.A.P.A.')).toBeTruthy()
    expect(screen.getByText(/Identidades de jugadores pendientes/)).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: /Arqueros/ }))
    fireEvent.click(screen.getByRole('button', { name: /Iniciar análisis y adjuntar video/ }))
    await waitFor(() => expect(api.enableCanonicalAnalysis).toHaveBeenCalledWith(16))
    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledWith(16, expect.objectContaining({ mode: 'video', profile: 'goalkeepers', source: null })))
  })

  it('shows the canonical preparation error without creating a review session', async () => {
    api.getPreloadedFixture.mockResolvedValue({ linked_match_id: 16, stage: { name: 'Apertura' }, scheduled_date: '2026-04-12', venue: null, unresolved_roster_players: 0 })
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Ci.De.Co. B', score: 41, players: [] }, away: { name: 'S.A.P.A.', score: 22, players: [] }, provenance: { filename: 'sheet.pdf', page_count: 1 }, pdf_available: false })
    api.enableCanonicalAnalysis.mockRejectedValue(new Error('a confirmed official sheet is required before canonical analysis can start'))
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/fixtures/fixture-16']}><Routes><Route path="/fixtures/:fixtureKey" element={<FixturePreparationPage />} /></Routes></MemoryRouter></QueryClientProvider>)

    await screen.findByText('Contexto oficial')
    fireEvent.click(screen.getByRole('button', { name: /Iniciar análisis y adjuntar video/ }))
    expect((await screen.findByRole('alert')).textContent).toContain('a confirmed official sheet is required before canonical analysis can start')
    expect(api.saveAnalysisSession).not.toHaveBeenCalled()
  })
})
