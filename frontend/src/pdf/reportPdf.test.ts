import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildPdfReport, orderedKeyEvents, reportFilename, warningRows } from './reportPdf'
import type { PdfReportInput } from './reportPdf'
import type { CanonicalEvent, Match, WarningsSummary } from '../types'

const text = vi.fn(); const save = vi.fn(); let document: { text: typeof text; setFontSize: ReturnType<typeof vi.fn>; save: typeof save; lastAutoTable: { finalY: number } }
const autoTable = vi.hoisted(() => vi.fn((doc: { lastAutoTable: { finalY: number } }) => { doc.lastAutoTable.finalY += 15 }))
vi.mock('jspdf', () => ({ jsPDF: class { constructor() { document = { text, setFontSize: vi.fn(), save, lastAutoTable: { finalY: 20 } }; return document } } }))
vi.mock('jspdf-autotable', () => ({ default: autoTable }))

const event = (sequence: number, state: CanonicalEvent['payload']['evidence_state'] = 'confirmed', uncertainty: string[] = [], video = false): CanonicalEvent => ({ id: sequence, sequence, active: true, payload: { kind: 'shot', period: 1, regulation_seconds: 60, clock_unverified: false, team_id: 1, player_id: null, outcome: 'goal', fact_kind: 'observed', evidence_state: state, uncertainty, note: 'private' }, evidence: video ? [{ id: sequence, kind: 'video', video_anchor_seconds: 2, uncertainty: [] }] : [] })
const comparison = { canonical: 1, official: 1, status: 'exact' as const, tolerance: 0 as const, canonical_event_ids: [1], evidence_ids: [] }
const warnings: WarningsSummary = { match_id: 1, official_snapshot_id: 's', players: [], match_totals: { metrics: { goals: comparison, yellow: comparison, two_minute: comparison, red: comparison, blue: comparison } }, limitations: [] }
const match = { id: 7, date: '2026/08/28', home_team: { name: 'Local' }, away_team: { name: 'Visitante' }, home_score: 20, away_score: 19 } as Match

describe('reportPdf', () => {
  beforeEach(() => { text.mockClear(); save.mockClear(); autoTable.mockClear() })
  it('uses a safe match filename with an absent-date fallback', () => {
    expect(reportFilename(match)).toBe('reporte-canonico-7-2026-08-28.pdf')
    expect(reportFilename({ ...match, date: '' })).toBe('reporte-canonico-7-sin-fecha.pdf')
  })
  it('ranks confirmed, lower-uncertainty, video-backed events and preserves sequence ties', () => {
    expect(orderedKeyEvents([event(4, 'ambiguous'), event(3, 'confirmed', ['x']), event(2, 'confirmed', [], true), event(1, 'confirmed')]).map(item => item.sequence)).toEqual([2, 1, 3, 4])
  })
  it('caps warning details and reveals linked-event omissions', () => {
    const manyIds = { ...comparison, canonical_event_ids: [1, 2, 3, 4, 5, 6] }
    expect(warningRows({ ...warnings, match_totals: { metrics: { ...warnings.match_totals.metrics, goals: manyIds } } })[0][4]).toContain('+1 omitidos')
  })
  const input = (overrides: Partial<Parameters<typeof buildPdfReport>[0]> = {}) => ({ match, state: { analytical_score: {}, possession: null, active_goalkeepers: {}, player_states: {}, discipline: [] }, metrics: { metrics: {}, official: null, reconciliation: [] }, reconciliation: { official: { snapshot_id: 's', home_score: 20, away_score: 19 }, reconciliation: [], discipline: [] }, warnings, events: [], ...overrides })
  it('prints the explicit evidence-priority ordering disclosure', () => {
    buildPdfReport(input()).save()
    const output = text.mock.calls.flat().join(' ')
    expect(output).toContain('confirmados, luego menor incertidumbre, luego evidencia con video')
    expect(output).toContain('Este orden NO es confianza')
  })
  it('states remaining warning comparisons and events omitted after report caps', () => {
    const cappedWarnings: WarningsSummary = { ...warnings, players: Array.from({ length: 4 }, (_, index) => ({ player: { id: index, name: `Jugador ${index}`, jersey_number: null, side: 'home' as const }, metrics: warnings.match_totals.metrics })) }
    buildPdfReport(input({ warnings: cappedWarnings, events: Array.from({ length: 31 }, (_, index) => event(index + 1)) })).save()
    const output = text.mock.calls.flat().join(' ')
    expect(output).toContain('5 comparaciones omitidas por límite del reporte')
    expect(output).toContain('1 eventos omitidos por límite del reporte')
    expect(save).toHaveBeenCalledWith('reporte-canonico-7-2026-08-28.pdf')
  })
  it('renders every required section with capped details and distinct official and observed scores', () => {
    const cappedWarnings: WarningsSummary = {
      ...warnings,
      match_totals: { metrics: { ...warnings.match_totals.metrics, goals: { ...comparison, canonical_event_ids: [1, 2, 3, 4, 5, 6] } } },
      players: Array.from({ length: 4 }, (_, index) => ({ player: { id: index, name: `Jugador ${index}`, jersey_number: null, side: 'home' as const }, metrics: warnings.match_totals.metrics })),
    }
    const completeInput = input({
      reconciliation: { official: { snapshot_id: 's', home_score: 25, away_score: 18 }, reconciliation: [{ side: 'home', official: 25, analytical: 20, discrepancy: 5 }], discipline: [] },
      warnings: cappedWarnings,
      events: Array.from({ length: 31 }, (_, index) => event(index + 1)),
      goalkeeper: { player: { id: 9, name: 'Arquero' }, metrics: { saves: 10, goals_conceded: 8, save_rate: { value: 0.55 } }, shot_map: { recorded: 18, missing_zone: 1, clock_unverified: 2, zones: { low_left: 3 } } } as unknown as PdfReportInput['goalkeeper'],
    }) as PdfReportInput

    buildPdfReport(completeInput).save()

    const output = text.mock.calls.flat().join(' ')
    expect(output).toContain('Marcador oficial: 25 - 18 · Observado: 20 - 19')
    expect(output).toContain('Reporte canónico de partido')
    expect(output).toContain('Estado canónico')
    expect(output).toContain('Cobertura y métricas canónicas')
    expect(output).toContain('Conciliación inmutable')
    expect(output).toContain('Advertencias: canónico / oficial')
    expect(output).toContain('5 comparaciones omitidas por límite del reporte')
    expect(output).toContain('Arquero: Arquero')
    expect(output).toContain('Zonas del arquero')
    expect(output).toContain('Eventos clave ordenados para exportación')
    expect(output).toContain('Eventos clave')
    expect(output).toContain('1 eventos omitidos por límite del reporte')
    expect(autoTable).toHaveBeenCalledTimes(7)
    const autoTableCalls = autoTable.mock.calls as unknown as Array<[unknown, { head: string[][]; body: string[][] }]>
    expect(autoTableCalls.map(([, options]) => options.head[0][0])).toEqual([
      'Marcador analítico', 'Métrica', 'Lado', 'Sujeto', 'Atajadas', 'Zona', 'Sec.',
    ])
    expect(autoTableCalls[3][1].body.flat()).toContain('#1, #2, #3, #4, #5 (+1 omitidos)')
    expect(save).toHaveBeenCalledWith('reporte-canonico-7-2026-08-28.pdf')
  })
})
