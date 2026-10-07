import type { CanonicalEventKind, EvidenceState } from './types'

const eventLabels: Record<CanonicalEventKind, string> = {
  shot: 'Lanzamiento', turnover: 'Pérdida', recovery: 'Recuperación', lineup_change: 'Cambio de jugadora/o',
  goalkeeper_change: 'Cambio de arquera/o', foul_sanction: 'Sanción', other: 'Incidencia de juego',
}

const evidenceLabels: Record<EvidenceState, string> = {
  confirmed: 'Confirmada', no_visible: 'No visible en video', ambiguous: 'Pendiente de confirmar', replay: 'Repetición',
}

export const eventLabel = (kind: CanonicalEventKind, outcome: string | null) => kind === 'other' && outcome === 'kickoff' ? 'Saque inicial' : eventLabels[kind]
export const evidenceLabel = (state: EvidenceState) => evidenceLabels[state]
export const matchTimeLabel = (seconds: number | null, unverified: boolean) => seconds !== null && !unverified
  ? `Tiempo oficial ${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`
  : 'Tiempo de partido pendiente de confirmar'
export const evidenceLabelForKind = (kind: string) => ({ video: 'Video', pdf: 'Planilla oficial', fixture: 'Fixture', unavailable: 'Sin evidencia disponible' }[kind] ?? 'Evidencia')
