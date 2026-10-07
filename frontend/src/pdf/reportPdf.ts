import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import type { CanonicalEvent, CanonicalMatchState, CanonicalPlayerProjection, Match, ReviewedMetrics, WarningComparison, WarningMetric, WarningsSummary } from '../types'

export type PdfReportInput = {
  match: Match
  state: CanonicalMatchState
  metrics: ReviewedMetrics
  reconciliation: Pick<ReviewedMetrics, 'official' | 'reconciliation' | 'discipline'>
  warnings: WarningsSummary
  events: CanonicalEvent[]
  goalkeeper?: CanonicalPlayerProjection
}

const COMPARISON_CAP = 20
const LINKED_IDS_CAP = 5
const EVENT_CAP = 30
const warningLabels: Record<WarningMetric, string> = { goals: 'Goles', yellow: 'Amarillas', two_minute: '2 min', red: 'Rojas', blue: 'Azules' }

const text = (value: unknown) => value === null || value === undefined || value === '' ? 'Sin dato' : String(value)
const clock = (event: CanonicalEvent) => event.payload.clock_unverified || event.payload.regulation_seconds === null
  ? 'No verificado'
  : `${Math.floor(event.payload.regulation_seconds / 60)}:${String(event.payload.regulation_seconds % 60).padStart(2, '0')}`

export function reportFilename(match: Pick<Match, 'id' | 'date'>) {
  const date = match.date?.replace(/[^0-9A-Za-z_-]/g, '-') || 'sin-fecha'
  return `reporte-canonico-${match.id}-${date}.pdf`
}

export function orderedKeyEvents(events: CanonicalEvent[]) {
  return events.filter(event => event.active).sort((a, b) => {
    const confirmed = Number(b.payload.evidence_state === 'confirmed') - Number(a.payload.evidence_state === 'confirmed')
    if (confirmed) return confirmed
    const uncertainty = a.payload.uncertainty.length - b.payload.uncertainty.length
    if (uncertainty) return uncertainty
    const video = Number(Boolean(b.evidence?.some(item => item.kind === 'video' && item.video_anchor_seconds !== null))) - Number(Boolean(a.evidence?.some(item => item.kind === 'video' && item.video_anchor_seconds !== null)))
    return video || a.sequence - b.sequence
  })
}

type WarningRow = [string, string, string, string, string]
export function warningRows(warnings: WarningsSummary): WarningRow[] {
  const comparisons: Array<[string, WarningMetric, WarningComparison]> = [
    ...Object.entries(warnings.match_totals.metrics).map(([metric, comparison]) => ['Total del partido', metric as WarningMetric, comparison] as [string, WarningMetric, WarningComparison]),
    ...warnings.players.flatMap(row => Object.entries(row.metrics).map(([metric, comparison]) => [row.player.name, metric as WarningMetric, comparison] as [string, WarningMetric, WarningComparison])),
  ]
  return comparisons.map(([subject, metric, comparison]) => {
    const ids = comparison.canonical_event_ids.slice(0, LINKED_IDS_CAP).map(id => `#${id}`).join(', ') || 'Sin vínculos'
    const omitted = comparison.canonical_event_ids.length - LINKED_IDS_CAP
    return [subject, warningLabels[metric], `${text(comparison.canonical)} / ${text(comparison.official)}`, comparison.status, `${ids}${omitted > 0 ? ` (+${omitted} omitidos)` : ''}`]
  })
}

function table(doc: jsPDF, title: string, head: string[], body: string[][], y: number) {
  doc.setFontSize(12); doc.text(title, 14, y)
  autoTable(doc, { startY: y + 3, head: [head], body, theme: 'grid', styles: { fontSize: 8, cellPadding: 2 }, headStyles: { fillColor: [49, 46, 129] } })
  return (doc as jsPDF & { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 10
}

export function buildPdfReport(input: PdfReportInput) {
  const doc = new jsPDF()
  let y = 16
  const official = input.reconciliation.official
  doc.setFontSize(18); doc.text('Reporte canónico de partido', 14, y); y += 8
  doc.setFontSize(10); doc.text(`${input.match.home_team?.name ?? 'Local'} vs ${input.match.away_team?.name ?? 'Visitante'} · ${text(input.match.date)}`, 14, y); y += 6
  doc.text(`Marcador oficial: ${official ? `${official.home_score} - ${official.away_score}` : 'sin snapshot'} · Observado: ${input.match.home_score} - ${input.match.away_score}`, 14, y); y += 10

  y = table(doc, 'Estado canónico', ['Marcador analítico', 'Posesión', 'Arqueros activos', 'Disciplina observada'], [[Object.entries(input.state.analytical_score).map(([side, score]) => `${side}: ${score}`).join(', ') || 'Sin dato', input.state.possession?.unresolved ? 'No resuelta' : text(input.state.possession?.start_basis), Object.entries(input.state.active_goalkeepers).map(([side, player]) => `${side}: ${text(player)}`).join(', ') || 'Sin dato', text(input.state.discipline.length)]], y)
  y = table(doc, 'Cobertura y métricas canónicas', ['Métrica', 'Conteo', 'Numerador', 'Denominador', 'Excl./desc./reloj'], Object.entries(input.metrics.metrics).map(([name, metric]) => [name, text(metric.count), text(metric.numerator), text(metric.denominator), `${metric.excluded}/${metric.unknown}/${metric.clock_unverified}`]), y)
  y = table(doc, 'Conciliación inmutable', ['Lado', 'Oficial', 'Analítico', 'Diferencia'], input.reconciliation.reconciliation.map(item => [item.side, text(item.official), text(item.analytical), text(item.discrepancy)]), y)

  const rows = warningRows(input.warnings)
  y = table(doc, 'Advertencias: canónico / oficial', ['Sujeto', 'Métrica', 'Canónico / oficial', 'Estado', 'Detalle estático'], rows.slice(0, COMPARISON_CAP), y)
  if (rows.length > COMPARISON_CAP) { doc.setFontSize(9); doc.text(`${rows.length - COMPARISON_CAP} comparaciones omitidas por límite del reporte.`, 14, y); y += 7 }

  if (input.goalkeeper) {
    const projection = input.goalkeeper
    y = table(doc, `Arquero: ${projection.player.name ?? projection.player.id}`, ['Atajadas', 'Goles recibidos', 'Tasa observada', 'Cobertura'], [[text(projection.metrics.saves), text(projection.metrics.goals_conceded), text(projection.metrics.save_rate ? `${Math.round(projection.metrics.save_rate.value * 100)}%` : null), `registrados ${projection.shot_map.recorded}; sin zona ${projection.shot_map.missing_zone}; reloj no verificado ${projection.shot_map.clock_unverified}`]], y)
    y = table(doc, 'Zonas del arquero', ['Zona', 'Conteo'], Object.entries(projection.shot_map.zones).map(([zone, count]) => [zone, text(count)]), y)
  }

  const events = orderedKeyEvents(input.events)
  doc.setFontSize(9); doc.text('Eventos clave ordenados para exportación: confirmados, luego menor incertidumbre, luego evidencia con video y secuencia. Este orden NO es confianza ni una puntuación autoritativa.', 14, y, { maxWidth: 180 }); y += 11
  y = table(doc, 'Eventos clave', ['Sec.', 'Período / reloj', 'Estado', 'Incertidumbre', 'Evidencias'], events.slice(0, EVENT_CAP).map(event => [text(event.sequence), `${event.payload.period} / ${clock(event)}`, event.payload.evidence_state, event.payload.uncertainty.join(', ') || 'Ninguna', event.evidence?.map(item => item.kind).join(', ') || 'Sin evidencia']), y)
  if (events.length > EVENT_CAP) { doc.setFontSize(9); doc.text(`${events.length - EVENT_CAP} eventos omitidos por límite del reporte.`, 14, y) }

  const filename = reportFilename(input.match)
  return { filename, save: () => doc.save(filename) }
}
