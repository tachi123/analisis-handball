import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CircleAlert, CircleCheck, CircleHelp, CircleX } from 'lucide-react'
import { getAnalysisSession, getCanonicalEvents } from '../api/client'
import { useYouTubeSync } from '../hooks/useYouTubeSync'
import { timelineRows } from '../reportTimeline'
import { seekTargetForEvent } from '../timelineInteractions'
import type { CanonicalEvent, VideoAvailabilityState, WarningComparison, WarningMetric, WarningStatus, WarningsSummary } from '../types'
import ReportEventTimeline from './ReportEventTimeline'

type Props = { matchId: number; summary: WarningsSummary }
const metrics: Array<{ key: WarningMetric; label: string }> = [
  { key: 'goals', label: 'Goles' }, { key: 'yellow', label: 'Amarillas' }, { key: 'two_minute', label: '2 min' }, { key: 'red', label: 'Rojas' }, { key: 'blue', label: 'Azules' },
]
const statusText: Record<WarningStatus, string> = {
  exact: 'Coincide', within_tolerance: 'Dentro de tolerancia', missing_in_canonical: 'Falta en análisis canónico', missing_in_official: 'Falta en planilla oficial', not_comparable: 'No comparable',
}
const statusStyle: Record<WarningStatus, string> = {
  exact: 'border-green-200 bg-green-50 text-green-800', within_tolerance: 'border-blue-200 bg-blue-50 text-blue-800', missing_in_canonical: 'border-amber-300 bg-amber-50 text-amber-900', missing_in_official: 'border-red-300 bg-red-50 text-red-900', not_comparable: 'border-gray-300 bg-gray-50 text-gray-700',
}
const unavailable = new Set<VideoAvailabilityState>(['unavailable', 'embedding_disabled', 'restricted', 'player_error'])

function Status({ comparison, id }: { comparison: WarningComparison; id: string }) {
  const Icon = comparison.status === 'exact' ? CircleCheck : comparison.status === 'not_comparable' ? CircleHelp : comparison.status === 'missing_in_official' ? CircleX : CircleAlert
  const description = `${statusText[comparison.status]}. Canónico ${comparison.canonical ?? 'sin dato'}; oficial ${comparison.official ?? 'sin dato'}.`
  return <span id={id} className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-xs font-medium ${statusStyle[comparison.status]}`} aria-label={description}><Icon size={15} aria-hidden="true" />{statusText[comparison.status]}<span className="sr-only">. {description}</span></span>
}

function comparisonValue(comparison: WarningComparison) { return `${comparison.canonical ?? '—'} / ${comparison.official ?? '—'}` }

export default function WarningsPanel({ matchId, summary }: Props) {
  const [expandedComparison, setExpandedComparison] = useState<string | null>(null)
  const [selected, setSelected] = useState<CanonicalEvent | null>(null)
  const [pendingSeekId, setPendingSeekId] = useState<number | null>(null)
  const [notice, setNotice] = useState('')
  const buttonRefs = useRef(new Map<string, HTMLButtonElement>())
  const eventsQuery = useQuery({ queryKey: ['canonical-events', matchId], queryFn: () => getCanonicalEvents(matchId), enabled: expandedComparison !== null, retry: false })
  const sessionQuery = useQuery({ queryKey: ['analysis-session', matchId], queryFn: () => getAnalysisSession(matchId), enabled: expandedComparison !== null, retry: false })
  const { availability, playerRef, seekTo } = useYouTubeSync(sessionQuery.data?.source ?? null, sessionQuery.data?.video_position_seconds ?? 0)
  const labels = useMemo(() => Object.fromEntries(summary.players.filter(row => row.player.id !== null).map(row => [row.player.id!, `${row.player.jersey_number === null ? '' : `#${row.player.jersey_number} `}${row.player.name}`])), [summary.players]) as Record<number, string>

  useEffect(() => {
    if (!selected || pendingSeekId !== selected.id) return
    const target = seekTargetForEvent(selected)
    if (target === null) {
      setPendingSeekId(null)
      setNotice(`Evento #${selected.sequence} seleccionado. Su evidencia no tiene un ancla de video reproducible.`)
      return
    }
    if (availability === 'ready' && playerRef.current) {
      seekTo(target)
      setPendingSeekId(null)
      setNotice(`Evento #${selected.sequence} seleccionado. Video movido a ${target.toFixed(1)} s.`)
      return
    }
    if (unavailable.has(availability) || (!sessionQuery.data?.source && !sessionQuery.isLoading)) {
      setPendingSeekId(null)
      setNotice(`Evento #${selected.sequence} seleccionado. El video no está disponible; la evidencia sigue disponible para lectura.`)
    }
  }, [availability, playerRef, pendingSeekId, seekTo, selected, sessionQuery.data?.source, sessionQuery.isLoading])

  const toggleComparison = (key: string, comparison: WarningComparison) => {
    if (expandedComparison === key) {
      setExpandedComparison(null)
      setSelected(null)
      setPendingSeekId(null)
      setNotice(`Detalle de ${key} contraído.`)
      requestAnimationFrame(() => buttonRefs.current.get(key)?.focus())
      return
    }
    setExpandedComparison(key)
    setSelected(null)
    setPendingSeekId(null)
    setNotice(`Detalle de ${key} expandido. Total oficial: ${comparison.official ?? 'sin dato'}.`)
  }
  const selectEvidence = (event: CanonicalEvent) => {
    setSelected(event)
    setPendingSeekId(seekTargetForEvent(event) === null ? null : event.id)
    setNotice(seekTargetForEvent(event) === null
      ? `Evento #${event.sequence} seleccionado. La evidencia no tiene video reproducible.`
      : `Evento #${event.sequence} seleccionado. Esperando que el reproductor de video esté listo.`)
  }
  const cell = (comparison: WarningComparison, key: string) => {
    const descriptionId = `warning-status-${key}`
    const detailId = `warning-detail-${key}`
    const contents = <><span className="font-semibold">{comparisonValue(comparison)}</span><Status comparison={comparison} id={descriptionId} /></>
    return comparison.canonical_event_ids.length
      ? <button ref={node => { if (node) buttonRefs.current.set(key, node); else buttonRefs.current.delete(key) }} type="button" className="flex w-full flex-col gap-1 rounded p-1 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700" aria-describedby={descriptionId} aria-expanded={expandedComparison === key} aria-controls={detailId} onClick={() => toggleComparison(key, comparison)}>{contents}</button>
      : <div className="flex flex-col gap-1 p-1">{contents}<span className="text-xs text-gray-600">No hay eventos canónicos vinculados.</span></div>
  }
  const detail = (comparison: WarningComparison, key: string) => {
    if (expandedComparison !== key) return null
    const linkedEvents = (eventsQuery.data ?? []).filter(event => comparison.canonical_event_ids.includes(event.id))
    return <tr key={`${key}-detail`} className="border-b bg-indigo-50/30"><td colSpan={metrics.length + 1} className="p-3"><section id={`warning-detail-${key}`} aria-label={`Detalle de ${key}`} className="space-y-3"><h3 className="font-medium">Evidencia canónica de advertencia (solo lectura)</h3><p className="text-sm">Total oficial inmutable: <b>{comparison.official ?? 'sin dato'}</b></p><section aria-label="Video de evidencia">{sessionQuery.data?.source && !unavailable.has(availability) ? <div ref={playerRef} className="aspect-video w-full" title="Video de evidencia del partido" /> : <p className="text-sm text-gray-600">No hay reproducción disponible; la evidencia no reproducible sigue disponible.</p>}</section>{eventsQuery.isLoading ? <p>Cargando evidencia…</p> : eventsQuery.isError ? <p role="alert">No se pudo cargar la evidencia canónica.</p> : linkedEvents.length ? <ReportEventTimeline variant="warning-detail" rows={timelineRows(linkedEvents, { playerId: 'all', kind: 'all', period: 'all', evidenceState: 'all' })} filters={{ playerId: 'all', kind: 'all', period: 'all', evidenceState: 'all' }} allEvents={linkedEvents} selected={selected} playerLabels={labels} notice="" onFiltersChange={() => undefined} onSelect={setSelected} onSeek={selectEvidence} /> : <p>No se encontraron eventos canónicos vinculados.</p>}</section></td></tr>
  }
  const playerRows = summary.players.flatMap((row, index) => {
    const rowKey = `player-${index}`
    return [<tr key={rowKey} className="border-b"><th className="p-2 font-medium">{row.player.jersey_number !== null ? `#${row.player.jersey_number} ` : ''}{row.player.name}<span className="block text-xs font-normal text-gray-500">{row.player.side === 'home' ? 'Local' : row.player.side === 'away' ? 'Visitante' : 'Sin lado'}</span></th>{metrics.map(metric => <td key={metric.key} className="p-2">{cell(row.metrics[metric.key], `${rowKey}-${metric.key}`)}</td>)}</tr>, ...metrics.map(metric => detail(row.metrics[metric.key], `${rowKey}-${metric.key}`)).filter(Boolean)]
  })
  return <section className="card space-y-3" aria-label="Advertencias canónicas y planilla oficial">
    <div><h2 className="font-semibold">Advertencias por jugador</h2><p className="text-sm text-gray-600">Comparación de totales canónicos elegibles con la planilla oficial inmutable. Los valores son canónico / oficial.</p></div>
    <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b text-xs text-gray-500"><th className="p-2">Jugador</th>{metrics.map(metric => <th key={metric.key} className="p-2">{metric.label}</th>)}</tr></thead><tbody><tr className="border-b bg-gray-50"><th className="p-2">Total del partido</th>{metrics.map(metric => <td key={metric.key} className="p-2">{cell(summary.match_totals.metrics[metric.key], `total-${metric.key}`)}</td>)}</tr>{metrics.map(metric => detail(summary.match_totals.metrics[metric.key], `total-${metric.key}`)).filter(Boolean)}{playerRows}</tbody></table></div>
    <section aria-label="Límites de comparación"><h3 className="font-medium">Límites de la fuente oficial</h3><ul className="mt-1 list-disc pl-5 text-sm text-gray-600">{summary.limitations.map(item => <li key={item.check}><b>{item.check}:</b> {item.reason} ({statusText[item.status]}).</li>)}</ul></section>
    <p role="status" aria-live="polite" className="text-sm">{notice}</p>
  </section>
}
