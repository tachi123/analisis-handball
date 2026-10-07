import { useEffect, useRef } from 'react'
import type { CanonicalEvent } from '../types'
import { videoAnchorSeconds } from '../timelineInteractions'
import { eventLabel, evidenceLabel, matchTimeLabel } from '../canonicalPresentation'

export { closestEventId } from '../timelineInteractions'

type Props = {
  events: CanonicalEvent[]
  selectedId: number | null
  highlightedId: number | null
  onSelect: (event: CanonicalEvent) => void
  onViewVideo?: (event: CanonicalEvent) => void
  onRevise: (event: CanonicalEvent) => void
  onDelete?: (event: CanonicalEvent) => void
  teamLabels?: Record<number, string>
  playerLabels?: Record<number, string>
  activeOnly?: boolean
}

export default function EventTimeline({ events, selectedId, highlightedId, onSelect, onViewVideo, onRevise, onDelete, teamLabels = {}, playerLabels = {}, activeOnly = true }: Props) {
  const rows = useRef(new Map<number, HTMLLIElement>())
  useEffect(() => { if (highlightedId) rows.current.get(highlightedId)?.scrollIntoView?.({ block: 'nearest' }) }, [highlightedId])
  const visibleEvents = (activeOnly ? events.filter(e => e.active) : [...events])
    .sort((left, right) => right.sequence - left.sequence)
  return <section className="card space-y-2" aria-label="Línea de tiempo de eventos">
    <h2 className="font-semibold">Eventos</h2>
    <p className="sr-only" aria-live="polite">{highlightedId ? `Evento ${highlightedId} resaltado por el video` : ''}</p>
    <ul className="space-y-2">{visibleEvents.map(event => {
       const videoTime = videoAnchorSeconds(event)
      const selected = event.id === selectedId || event.id === highlightedId
      const isDeleted = !event.active
      return <li key={event.id} ref={node => { if (node) rows.current.set(event.id, node); else rows.current.delete(event.id) }} className={`rounded border p-2 ${selected ? 'border-indigo-600 bg-indigo-50' : ''} ${isDeleted ? 'opacity-50 bg-gray-100' : ''}`}>
        <button className="review-target w-full text-left" aria-current={selected || undefined} onClick={() => onSelect(event)} onKeyDown={e => { if (e.key === 'Enter') onSelect(event) }}>
           <b>#{event.sequence} · {eventLabel(event.payload.kind, event.payload.outcome)}</b> · {evidenceLabel(event.payload.evidence_state)}
            <span className="block text-xs text-gray-600">{event.payload.team_id === null ? 'Equipo sin asignar' : teamLabels[event.payload.team_id] ?? `Equipo #${event.payload.team_id}`} · {matchTimeLabel(event.payload.regulation_seconds, event.payload.clock_unverified)}</span>
           {event.payload.kind === 'shot' && <span className="block text-xs text-gray-600">{event.payload.player_id === null ? 'Tirador sin asignar' : `Tirador: ${playerLabels[event.payload.player_id] ?? `Jugador #${event.payload.player_id}`}`}{event.payload.goalkeeper_id === null || event.payload.goalkeeper_id === undefined ? '' : ` · Arquero rival: ${playerLabels[event.payload.goalkeeper_id] ?? `Jugador #${event.payload.goalkeeper_id}`}`}</span>}
          {isDeleted && <span className="ml-2 rounded bg-red-100 px-1 text-xs text-red-800" aria-label="Eliminado">eliminado</span>}
            <span className="block text-xs text-gray-600">{videoTime === null ? 'Evidencia de video no disponible.' : `Video ${videoTime.toFixed(1)} s`}</span>
        </button>
        <div className="mt-1 flex gap-2">
           <button className="review-target text-sm underline" onClick={() => onRevise(event)}>Editar incidencia</button>
           {videoTime !== null && onViewVideo && <button className="review-target text-sm underline" onClick={() => onViewVideo(event)}>Ver en video</button>}
          {onDelete && !isDeleted && <button className="review-target text-sm underline text-red-600" onClick={() => onDelete(event)}>Eliminar</button>}
        </div>
      </li>
    })}</ul>
    {visibleEvents.length === 0 && <p className="text-sm text-gray-500">Todavía no hay eventos canónicos.</p>}
  </section>
}
