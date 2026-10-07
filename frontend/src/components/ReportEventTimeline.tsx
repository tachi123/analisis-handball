import { useRef } from 'react'
import { type ReportFilters, type TimelineRow } from '../reportTimeline'
import type { CanonicalEvent, CanonicalEventKind, EvidenceState } from '../types'
import { videoAnchorSeconds } from '../timelineInteractions'
import { eventLabel, evidenceLabel, evidenceLabelForKind, matchTimeLabel } from '../canonicalPresentation'

type Props = {
  rows: TimelineRow[]
  filters: ReportFilters
  allEvents: CanonicalEvent[]
  selected: CanonicalEvent | null
  playerLabels: Record<number, string>
  teamLabels?: Record<number, string>
  notice: string
  onFiltersChange: (filters: ReportFilters) => void
  onSelect: (event: CanonicalEvent) => void
  onSeek?: (event: CanonicalEvent) => void
  variant?: 'default' | 'warning-detail'
}

const value = <T extends string | number>(item: T | 'all') => String(item)

function EventDetailPanel({ event, playerLabels, teamLabels }: { event: CanonicalEvent | null; playerLabels: Record<number, string>; teamLabels: Record<number, string> }) {
  if (!event) return <section className="card" aria-label="Detalle del evento"><h2 className="font-semibold">Detalle del evento</h2><p className="text-sm text-gray-600">Seleccioná un evento para ver su estado canónico actual.</p></section>
  const player = event.payload.player_id === null ? 'Sin jugador responsable' : playerLabels[event.payload.player_id] ?? `Jugador desconocido #${event.payload.player_id}`
  const related = event.payload.related_player_id === null || event.payload.related_player_id === undefined ? null : playerLabels[event.payload.related_player_id] ?? `Jugador desconocido #${event.payload.related_player_id}`
  const team = event.payload.team_id === null ? 'Equipo sin asignar' : teamLabels[event.payload.team_id] ?? `Equipo #${event.payload.team_id}`
  return <section className="card space-y-2" aria-label="Detalle del evento" aria-live="polite"><h2 className="font-semibold">Detalle del evento #{event.sequence}</h2><dl className="grid gap-1 text-sm"><div><dt className="inline font-medium">Equipo: </dt><dd className="inline">{team}</dd></div><div><dt className="inline font-medium">Tipo: </dt><dd className="inline">{eventLabel(event.payload.kind, event.payload.outcome)}</dd></div><div><dt className="inline font-medium">Jugador: </dt><dd className="inline">{player}</dd></div>{related && <div><dt className="inline font-medium">Relacionado: </dt><dd className="inline">{related}</dd></div>}<div><dt className="inline font-medium">Estado de evidencia: </dt><dd className="inline">{evidenceLabel(event.payload.evidence_state)}</dd></div><div><dt className="inline font-medium">Tiempo: </dt><dd className="inline">{matchTimeLabel(event.payload.regulation_seconds, event.payload.clock_unverified)}</dd></div></dl><section><h3 className="font-medium text-sm">Evidencia actual</h3>{event.evidence?.length ? <ul className="list-disc pl-5 text-sm">{event.evidence.map(item => <li key={item.id}>{evidenceLabelForKind(item.kind)}{typeof item.video_anchor_seconds === 'number' ? ` · video ${item.video_anchor_seconds.toFixed(1)} s` : ''}</li>)}</ul> : <p className="text-sm text-gray-600">Sin evidencia adjunta.</p>}</section></section>
}

export default function ReportEventTimeline({ rows, filters, allEvents, selected, playerLabels, teamLabels = {}, notice, onFiltersChange, onSelect, onSeek, variant = 'default' }: Props) {
  const rowRefs = useRef(new Map<number, HTMLButtonElement>())
  const players = [...new Set(allEvents.map(event => event.payload.player_id).filter((id): id is number => id !== null))].sort((a, b) => (playerLabels[a] ?? String(a)).localeCompare(playerLabels[b] ?? String(b)))
  const kinds = [...new Set(allEvents.map(event => event.payload.kind))].sort()
  const periods = [...new Set(allEvents.map(event => event.payload.period))].sort((a, b) => a - b)
  const evidenceStates = [...new Set(allEvents.map(event => event.payload.evidence_state))].sort()
  const selectAt = (index: number) => { const row = rows[index]; if (!row) return; onSelect(row.event); rowRefs.current.get(row.event.id)?.focus() }
  const onRowKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (event.key === 'ArrowDown') { event.preventDefault(); selectAt(Math.min(rows.length - 1, index + 1)) }
    if (event.key === 'ArrowUp') { event.preventDefault(); selectAt(Math.max(0, index - 1)) }
    if (event.key === 'Home') { event.preventDefault(); selectAt(0) }
    if (event.key === 'End') { event.preventDefault(); selectAt(rows.length - 1) }
  }
  const update = <K extends keyof ReportFilters>(key: K, raw: string) => onFiltersChange({ ...filters, [key]: raw === 'all' ? 'all' : key === 'kind' || key === 'evidenceState' ? raw : Number(raw) } as ReportFilters)
  if (variant === 'warning-detail') return <section aria-label="Eventos canónicos vinculados" className="space-y-2"><h4 className="font-medium">Eventos canónicos vinculados</h4><ol className="space-y-2">{rows.map(row => {
    const event = row.event; const player = event.payload.player_id === null ? 'Sin jugador responsable' : playerLabels[event.payload.player_id] ?? `Jugador desconocido #${event.payload.player_id}`; const anchor = videoAnchorSeconds(event); const canSeek = anchor !== null
    return <li key={event.id} className={`rounded border p-3 text-sm ${selected?.id === event.id ? 'border-indigo-600 bg-indigo-50' : ''}`} aria-current={selected?.id === event.id || undefined}><p><b>{eventLabel(event.payload.kind, event.payload.outcome)}</b></p><dl className="grid gap-1"><div><dt className="inline font-medium">Jugador: </dt><dd className="inline">{player}</dd></div><div><dt className="inline font-medium">Tiempo: </dt><dd className="inline">{matchTimeLabel(event.payload.regulation_seconds, event.payload.clock_unverified)}</dd></div><div><dt className="inline font-medium">Tiempo de video: </dt><dd className="inline">{anchor === null ? 'sin ancla' : `${anchor.toFixed(1)} s`}</dd></div></dl>{canSeek && onSeek ? <button type="button" className="btn mt-2" onClick={() => onSeek(event)}>Ver evidencia de video</button> : <p className="mt-2 text-xs text-gray-600">La evidencia no tiene video reproducible.</p>}</li>
  })}</ol></section>
  return <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.8fr)]"><section className="card space-y-3" aria-label="Línea de tiempo canónica">
    <div><h2 className="font-semibold">Línea de tiempo canónica</h2><p className="text-sm text-gray-600">Usá Flecha arriba/abajo, Inicio o Fin sobre un evento para navegar los resultados visibles.</p></div>
    <div className="grid gap-2 sm:grid-cols-2"><label className="text-sm">Jugador<select aria-label="Filtrar por jugador" className="mt-1 w-full rounded border p-2" value={value(filters.playerId)} onChange={event => update('playerId', event.target.value)}><option value="all">Todos</option>{players.map(id => <option key={id} value={id}>{playerLabels[id] ?? `Jugador desconocido #${id}`}</option>)}</select></label><label className="text-sm">Tipo<select aria-label="Filtrar por tipo" className="mt-1 w-full rounded border p-2" value={filters.kind} onChange={event => update('kind', event.target.value)}><option value="all">Todos</option>{kinds.map((kind: CanonicalEventKind) => <option key={kind} value={kind}>{eventLabel(kind, null)}</option>)}</select></label><label className="text-sm">Período<select aria-label="Filtrar por período" className="mt-1 w-full rounded border p-2" value={value(filters.period)} onChange={event => update('period', event.target.value)}><option value="all">Todos</option>{periods.map(period => <option key={period} value={period}>{period}</option>)}</select></label><label className="text-sm">Estado de evidencia<select aria-label="Filtrar por estado de evidencia" className="mt-1 w-full rounded border p-2" value={filters.evidenceState} onChange={event => update('evidenceState', event.target.value)}><option value="all">Todos</option>{evidenceStates.map((state: EvidenceState) => <option key={state} value={state}>{evidenceLabel(state)}</option>)}</select></label></div>
    <button type="button" className="btn" onClick={() => onFiltersChange({ playerId: 'all', kind: 'all', period: 'all', evidenceState: 'all' })}>Limpiar filtros</button>
    <p role="status" aria-live="polite" className="text-sm">{rows.length} eventos visibles. {notice}</p>
    <ol className="space-y-2">{rows.map((row, index) => { const selectedRow = selected?.id === row.event.id; const anchor = videoAnchorSeconds(row.event); const team = row.event.payload.team_id === null ? 'Equipo sin asignar' : teamLabels[row.event.payload.team_id] ?? `Equipo #${row.event.payload.team_id}`; return <li key={row.event.id}><button ref={node => { if (node) rowRefs.current.set(row.event.id, node); else rowRefs.current.delete(row.event.id) }} type="button" className={`w-full rounded border p-3 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700 ${selectedRow ? 'border-indigo-600 bg-indigo-50' : ''}`} aria-current={selectedRow || undefined} onClick={() => onSelect(row.event)} onKeyDown={event => onRowKeyDown(event, index)}><b>#{row.event.sequence} · {eventLabel(row.event.payload.kind, row.event.payload.outcome)}</b> · {team}<span className="block text-sm">{matchTimeLabel(row.event.payload.regulation_seconds, row.event.payload.clock_unverified)}</span><span className="block text-xs text-gray-600">{anchor === null ? 'Sin ancla de video.' : `Ancla de video ${anchor.toFixed(1)} s.`}</span></button></li> })}</ol>
    {rows.length === 0 && <p className="text-sm text-gray-600">No hay eventos que coincidan con los filtros.</p>}
   </section><EventDetailPanel event={selected} playerLabels={playerLabels} teamLabels={teamLabels} /></div>
}
