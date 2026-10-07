import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Match, ReportPublicationStatus, ReviewedReportPackage } from '../types'
import StatisticsPage from './StatisticsPage'

const api = vi.hoisted(() => ({
  attestRecoveryArtifact: vi.fn(), createReportPackage: vi.fn(), getEvents: vi.fn(), getMatch: vi.fn(),
  getPublicationStatus: vi.fn(), getReviewedMetrics: vi.fn(), getCanonicalMetrics: vi.fn(), getCanonicalReconciliation: vi.fn(), getCanonicalState: vi.fn(), getCanonicalEvents: vi.fn(), getCanonicalPlayerProjection: vi.fn(), getWarningsSummary: vi.fn(), publishReportPackage: vi.fn(), approveReportPackage: vi.fn(),
}))
vi.mock('../api/client', () => api)

const packageRecord = { id: 7, match_id: 1, report_version: 3, schema_version: 'public-report-v1', approved_at: '2026-08-23T10:00:00Z', coaching_question: 'Q', pattern_statement: 'P', action_kind: 'keep', action_text: 'A', uncertainty_disclosure: 'U', metrics: {}, reconciliation: [], source_label: null, source_status: null, evidence: [] } as ReviewedReportPackage
const match = { id: 1, date: '2026-08-23', home_team: { id: 1, name: 'SAPA' }, away_team: { id: 2, name: 'Rival' }, squad: [] } as unknown as Match
const status = (state: ReportPublicationStatus['status'], overrides: Partial<ReportPublicationStatus> = {}): ReportPublicationStatus => ({ package_id: 7, report_version: 3, status: state, missing_recovery_artifacts: [], recovery_artifacts: [], published_at: null, failure_message: null, public_url: null, ...overrides })

function renderPage() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/match/1/stats']}><Routes><Route path="/match/:matchId/stats" element={<StatisticsPage />} /></Routes></MemoryRouter></QueryClientProvider>)
}

async function createApprovedPackage() {
  fireEvent.click(await screen.findByRole('radio', { name: 'Mantener' }))
  fireEvent.click(screen.getByRole('button', { name: 'Crear paquete para revisión' }))
  await screen.findByLabelText('Publicación del informe')
}

describe('StatisticsPage publication controls', () => {
  beforeEach(() => {
    api.getMatch.mockResolvedValue(match)
    api.getEvents.mockResolvedValue([])
    api.getReviewedMetrics.mockResolvedValue({ metrics: {}, official: null, reconciliation: [] })
    api.getCanonicalMetrics.mockResolvedValue({ metrics: { shots: { name: 'shots', count: 1, numerator: 1, denominator: 1, excluded: 0, unknown: 0, clock_unverified: 0, evidence: [{ event_id: 1, revision_id: 1 }] } }, eligibility: { eligible: 1, excluded: 0, unknown: 0, unresolved: 0, clock_unverified: 0 } })
    api.getCanonicalReconciliation.mockResolvedValue({ official: null, reconciliation: [] })
    api.getCanonicalState.mockResolvedValue({ analytical_score: {}, possession: null, active_goalkeepers: {}, player_states: {}, discipline: [] })
    api.getCanonicalEvents.mockResolvedValue([])
    api.getWarningsSummary.mockResolvedValue({ match_id: 1, official_snapshot_id: 'snapshot-1', players: [], match_totals: { metrics: { goals: { canonical: 1, official: 1, status: 'exact', tolerance: 0, canonical_event_ids: [1], evidence_ids: [2] }, yellow: { canonical: 0, official: 0, status: 'exact', tolerance: 0, canonical_event_ids: [], evidence_ids: [] }, two_minute: { canonical: 0, official: 0, status: 'exact', tolerance: 0, canonical_event_ids: [], evidence_ids: [] }, red: { canonical: 0, official: 0, status: 'exact', tolerance: 0, canonical_event_ids: [], evidence_ids: [] }, blue: { canonical: 0, official: 0, status: 'exact', tolerance: 0, canonical_event_ids: [], evidence_ids: [] } } }, limitations: [] })
    api.createReportPackage.mockResolvedValue(packageRecord)
    api.attestRecoveryArtifact.mockResolvedValue({})
  })
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('shows missing recovery artifacts and keeps publication disabled', async () => {
    api.getPublicationStatus.mockResolvedValue(status('not_ready', { missing_recovery_artifacts: ['postgres_dump', 'imported_pdf_export'] }))
    renderPage()
    await createApprovedPackage()
    expect(await screen.findByText('Faltan: postgres_dump, imported_pdf_export')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Publicar' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('registers an operator attestation and enables ready publication', async () => {
    api.getPublicationStatus.mockResolvedValue(status('ready'))
    renderPage()
    await createApprovedPackage()
    fireEvent.change(screen.getByLabelText('Ubicación del dump PostgreSQL'), { target: { value: '/backups/match.sql' } })
    fireEvent.click(screen.getByRole('button', { name: 'Registrar dump' }))
    await waitFor(() => expect(api.attestRecoveryArtifact).toHaveBeenCalledWith(7, 'postgres_dump', '/backups/match.sql'))
    expect((await screen.findByRole('button', { name: 'Publicar' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('shows a pending publish state without claiming success', async () => {
    api.getPublicationStatus.mockResolvedValue(status('ready'))
    api.publishReportPackage.mockReturnValue(new Promise(() => {}))
    renderPage()
    await createApprovedPackage()
    fireEvent.click(await screen.findByRole('button', { name: 'Publicar' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Publicando...' })).toBeTruthy())
    expect((screen.getByRole('button', { name: 'Publicando...' }) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.queryByRole('link', { name: 'Abrir informe público actual' })).toBeNull()
  })

  it('offers retry after failure and links only the published current report', async () => {
    api.getPublicationStatus.mockResolvedValue(status('failed', { failure_message: 'Publication failed. Retry the publication.' }))
    api.publishReportPackage.mockResolvedValue(status('published', { published_at: '2026-08-23T11:00:00Z', public_url: 'http://localhost:5174' }))
    renderPage()
    await createApprovedPackage()
    expect((await screen.findByRole('alert')).textContent).toContain('Publication failed. Retry the publication.')
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar publicación' }))
    expect((await screen.findByRole('link', { name: 'Abrir informe público actual' })).getAttribute('href')).toBe('http://localhost:5174')
  })

  it('blocks tactical report creation when canonical evidence is unavailable', async () => {
    api.getCanonicalMetrics.mockResolvedValue({ metrics: {}, eligibility: { eligible: 0, excluded: 1, unknown: 1, unresolved: 1, clock_unverified: 1 } })
    renderPage()
    expect(await screen.findByText('No hay evidencia elegible; las conclusiones tácticas están bloqueadas.')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Crear paquete para revisión' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('loads and renders the match-scoped warnings panel', async () => {
    renderPage()
    expect(await screen.findByLabelText('Advertencias canónicas y planilla oficial')).toBeTruthy()
    expect(api.getWarningsSummary).toHaveBeenCalledWith(1)
  })
})
