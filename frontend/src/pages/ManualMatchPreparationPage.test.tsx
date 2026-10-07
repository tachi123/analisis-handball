import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ManualMatchPreparationPage from './ManualMatchPreparationPage'

const api = vi.hoisted(() => ({ confirmMatchPDF: vi.fn(), enableCanonicalAnalysis: vi.fn(), getMatch: vi.fn(), getOfficialSheet: vi.fn(), previewMatchPDF: vi.fn(), saveAnalysisSession: vi.fn() }))
vi.mock('../api/client', () => api)

const match = { id: 7, home_team: { id: 1, name: 'Home' }, away_team: { id: 2, name: 'Away' }, tournament: null }
const preview = (overrides = {}) => ({
  match_id: 7,
  preview: { match_info: { home_score: 2, away_score: 1 }, home_team: { name: 'Home', players: [] }, away_team: { name: 'Away', players: [] }, warnings: ['parser warning'] },
  home_compatibility: { status: 'compatible', expected_name: 'Home', parsed_name: 'Home' },
  away_compatibility: { status: 'compatible', expected_name: 'Away', parsed_name: 'Away' },
  score_reconciliation: 'match', date_reconciliation: 'match', warnings: ['parser warning'],
  ...overrides,
})

function renderPage() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/matches/7/prepare']}><Routes><Route path="/matches/:matchId/prepare" element={<ManualMatchPreparationPage />} /><Route path="/match/:matchId/review" element={<p>review</p>} /></Routes></MemoryRouter></QueryClientProvider>)
}

describe('ManualMatchPreparationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getMatch.mockResolvedValue(match)
    api.getOfficialSheet.mockRejectedValue({ response: { status: 404 } })
    api.previewMatchPDF.mockResolvedValue(preview())
    api.confirmMatchPDF.mockResolvedValue({ match_id: 7, snapshot_id: 'sheet', reused: false })
    api.enableCanonicalAnalysis.mockResolvedValue({ canonical_analysis_enabled: true })
    api.saveAnalysisSession.mockResolvedValue({})
  })

  it('does not require acknowledgement for parser warnings alone', async () => {
    renderPage()
    await screen.findByText('Cargar y revisar planilla oficial')
    fireEvent.change(screen.getByLabelText('Archivo PDF'), { target: { files: [new File(['pdf'], 'sheet.pdf', { type: 'application/pdf' })] } })
    fireEvent.click(screen.getByRole('button', { name: 'Revisar PDF' }))
    await screen.findByText('parser warning')

    expect(screen.queryByLabelText(/Reconozco las discrepancias/)).toBeNull()
    expect(screen.getByRole('button', { name: 'Confirmar planilla' })).not.toHaveProperty('disabled', true)
  })

  it('requires acknowledgement only for explicit reconciliation mismatches', async () => {
    api.previewMatchPDF.mockResolvedValue(preview({ score_reconciliation: 'mismatch' }))
    renderPage()
    await screen.findByText('Cargar y revisar planilla oficial')
    fireEvent.change(screen.getByLabelText('Archivo PDF'), { target: { files: [new File(['pdf'], 'sheet.pdf', { type: 'application/pdf' })] } })
    fireEvent.click(screen.getByRole('button', { name: 'Revisar PDF' }))
    const confirm = await screen.findByRole('button', { name: 'Confirmar planilla' })

    expect(screen.getByLabelText(/Reconozco las discrepancias/)).toBeTruthy()
    expect((confirm as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByLabelText(/Reconozco las discrepancias/))
    expect((confirm as HTMLButtonElement).disabled).toBe(false)
  })

  it('hands a confirmed manual match to canonical video analysis', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar análisis de video' }))

    await waitFor(() => expect(api.enableCanonicalAnalysis).toHaveBeenCalledWith(7))
    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledWith(7, expect.objectContaining({ mode: 'video', profile: 'complete' })))
    expect(await screen.findByText('review')).toBeTruthy()
  })

  it('shows an actionable error instead of treating an access failure as a missing sheet', async () => {
    api.getOfficialSheet.mockRejectedValue({ response: { status: 403 } })
    renderPage()

    expect((await screen.findByRole('alert')).textContent).toContain('No se pudo consultar la planilla oficial')
    expect(screen.queryByText('Cargar y revisar planilla oficial')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() => expect(api.getOfficialSheet).toHaveBeenCalledTimes(2))
  })

  it('surfaces a cutover or session-creation failure', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    api.enableCanonicalAnalysis.mockRejectedValue(new Error('cutover denied'))
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar análisis de video' }))

    expect((await screen.findByRole('alert')).textContent).toContain('cutover denied')
    expect(api.saveAnalysisSession).not.toHaveBeenCalled()
  })

  it('preserves a successful cutover when creating the initial session fails and retries only the session', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    api.saveAnalysisSession.mockRejectedValueOnce(new Error('session unavailable')).mockResolvedValueOnce({})
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar análisis de video' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('El análisis canónico ya fue habilitado')
    expect(alert.textContent).toContain('La habilitación no se revirtió')
    expect(api.enableCanonicalAnalysis).toHaveBeenCalledTimes(1)
    expect(api.saveAnalysisSession).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar inicio de análisis' }))
    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledTimes(2))
    expect(api.enableCanonicalAnalysis).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('review')).toBeTruthy()
  })
})
