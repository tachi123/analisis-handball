import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ManualMatchPreparationPage from './ManualMatchPreparationPage'

const api = vi.hoisted(() => ({ confirmMatchPDF: vi.fn(), createAnalysisRun: vi.fn(), getAnalysisRuns: vi.fn(), getMatch: vi.fn(), getOfficialSheet: vi.fn(), previewMatchPDF: vi.fn(), saveAnalysisSession: vi.fn() }))
vi.mock('../api/client', () => api)

const match = { id: 7, home_team: { id: 1, name: 'Home' }, away_team: { id: 2, name: 'Away' }, tournament: null, youtube_link: null }
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
    api.getAnalysisRuns.mockResolvedValue([])
    api.createAnalysisRun.mockResolvedValue({ id: 21, mode: 'video', status: 'draft' })
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

  it('creates a selected draft and its session before opening the review', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('radio', { name: 'Video local manual' }))
    fireEvent.click(screen.getByRole('button', { name: 'Crear borrador' }))

    await waitFor(() => expect(api.createAnalysisRun).toHaveBeenCalledWith(7, 'manual'))
    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledWith(7, expect.objectContaining({ mode: 'manual', profile: 'complete' }), 21))
    expect(await screen.findByText('review')).toBeTruthy()
  })

  it('seeds a video draft session with the imported YouTube link', async () => {
    api.getMatch.mockResolvedValue({ ...match, youtube_link: 'https://youtu.be/abcdefghijk' })
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('button', { name: 'Crear borrador' }))

    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledWith(7, expect.objectContaining({
      mode: 'video',
      source: { url: 'https://youtu.be/abcdefghijk', availability_state: 'unknown' },
    }), 21))
  })

  it('resumes a persisted draft after reload without recreating or reseeding it', async () => {
    api.getMatch.mockResolvedValue({ ...match, youtube_link: 'https://youtu.be/abcdefghijk' })
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    api.getAnalysisRuns.mockResolvedValue([{ id: 34, match_id: 7, mode: 'video', status: 'draft' }])
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    await screen.findByText('Borrador existente:')

    fireEvent.click(screen.getAllByRole('button', { name: 'Retomar borrador' })[0])

    expect(await screen.findByText('review')).toBeTruthy()
    expect(api.createAnalysisRun).not.toHaveBeenCalled()
    expect(api.saveAnalysisSession).not.toHaveBeenCalled()
  })

  it('creates a draft when persisted drafts use a different mode', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    api.getAnalysisRuns.mockResolvedValue([{ id: 34, match_id: 7, mode: 'manual', status: 'draft' }])
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    await screen.findByText('Borrador existente:')
    fireEvent.click(screen.getByRole('button', { name: 'Crear borrador' }))

    await waitFor(() => expect(api.createAnalysisRun).toHaveBeenCalledWith(7, 'video'))
    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledWith(7, expect.objectContaining({ mode: 'video' }), 21))
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

  it('surfaces a draft-creation failure without trying to save a session', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    api.createAnalysisRun.mockRejectedValue(new Error('draft denied'))
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('button', { name: 'Crear borrador' }))

    expect((await screen.findByRole('alert')).textContent).toContain('draft denied')
    expect(api.saveAnalysisSession).not.toHaveBeenCalled()
  })

  it('keeps a created draft when creating its initial session fails', async () => {
    api.getOfficialSheet.mockResolvedValue({ home: { name: 'Home', score: 2 }, away: { name: 'Away', score: 1 } })
    api.saveAnalysisSession.mockRejectedValueOnce(new Error('session unavailable')).mockResolvedValueOnce({})
    renderPage()
    await screen.findByText('Planilla oficial confirmada')
    fireEvent.click(screen.getByRole('button', { name: 'Crear borrador' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toContain('El borrador ya fue creado')
    expect(alert.textContent).toContain('mismo borrador')
    expect(api.createAnalysisRun).toHaveBeenCalledTimes(1)
    expect(api.saveAnalysisSession).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Reintentar inicio de análisis' }))
    await waitFor(() => expect(api.saveAnalysisSession).toHaveBeenCalledTimes(2))
    expect(api.createAnalysisRun).toHaveBeenCalledTimes(1)
    expect(await screen.findByText('review')).toBeTruthy()
  })
})
