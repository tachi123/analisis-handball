import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Match } from '../types'
import PdfReportExport from './PdfReportExport'

const api = vi.hoisted(() => ({ getMatch: vi.fn(), getCanonicalState: vi.fn(), getCanonicalMetrics: vi.fn(), getCanonicalReconciliation: vi.fn(), getWarningsSummary: vi.fn(), getCanonicalEvents: vi.fn(), getCanonicalPlayerProjection: vi.fn() }))
const buildPdfReport = vi.hoisted(() => vi.fn(() => ({ save: vi.fn() })))
vi.mock('../api/client', () => api)
vi.mock('../pdf/reportPdf', () => ({ buildPdfReport }))
const match = { id: 1, date: '2026-08-28', squad: [{ player_id: 9, is_goalkeeper: true, player: { name: 'Arquero' } }, { player_id: 3, is_goalkeeper: false, player: { name: 'Campo' } }] } as unknown as Match
const renderControl = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><PdfReportExport matchId={1} /></QueryClientProvider>)

describe('PdfReportExport', () => {
  beforeEach(() => {
    api.getMatch.mockResolvedValue(match); api.getCanonicalState.mockResolvedValue({}); api.getCanonicalMetrics.mockResolvedValue({}); api.getCanonicalReconciliation.mockResolvedValue({}); api.getWarningsSummary.mockResolvedValue({}); api.getCanonicalEvents.mockResolvedValue([]); api.getCanonicalPlayerProjection.mockResolvedValue({ player: {}, metrics: {}, shot_map: {} }); buildPdfReport.mockClear()
  })
  afterEach(() => { cleanup(); vi.clearAllMocks() })
  it('stays disabled until all required reads are ready', () => {
    api.getMatch.mockReturnValue(new Promise(() => {})); renderControl()
    expect((screen.getByRole('button', { name: 'Preparando reporte…' }) as HTMLButtonElement).disabled).toBe(true)
  })
  it('shows a required-read error and blocks export', async () => {
    api.getCanonicalEvents.mockRejectedValue(new Error('unavailable')); renderControl()
    expect((await screen.findByRole('alert')).textContent).toContain('No se pudo cargar la información canónica requerida')
    expect((screen.getByRole('button', { name: 'Exportar reporte PDF' }) as HTMLButtonElement).disabled).toBe(true)
  })
  it('exports without goalkeeper and lazily loads only a selected eligible goalkeeper', async () => {
    renderControl(); const button = await screen.findByRole('button', { name: 'Exportar reporte PDF' }); await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(button); await waitFor(() => expect(buildPdfReport).toHaveBeenCalledWith(expect.objectContaining({ goalkeeper: undefined })))
    expect(api.getCanonicalPlayerProjection).not.toHaveBeenCalled()
    expect(screen.queryByRole('option', { name: 'Campo' })).toBeNull()
    fireEvent.change(screen.getByLabelText('Arquero opcional para PDF'), { target: { value: '9' } })
    await waitFor(() => expect(api.getCanonicalPlayerProjection).toHaveBeenCalledWith(1, { player_id: 9 }))
    await waitFor(() => expect((screen.getByRole('button', { name: 'Exportar reporte PDF' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: 'Exportar reporte PDF' }))
    await waitFor(() => expect(buildPdfReport).toHaveBeenLastCalledWith(expect.objectContaining({ goalkeeper: expect.objectContaining({ player: {} }) })))
  })
  it('blocks export when the selected goalkeeper projection fails', async () => {
    api.getCanonicalPlayerProjection.mockRejectedValue(new Error('unavailable')); renderControl()
    await screen.findByRole('button', { name: 'Exportar reporte PDF' })
    fireEvent.change(screen.getByLabelText('Arquero opcional para PDF'), { target: { value: '9' } })
    expect((await screen.findByRole('alert')).textContent).toContain('No se pudo cargar la proyección del arquero seleccionado')
    expect((screen.getByRole('button', { name: 'Exportar reporte PDF' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Exportar reporte PDF' }))
    expect(buildPdfReport).not.toHaveBeenCalled()
  })
})
