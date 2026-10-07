import { useEffect, useRef, useState } from 'react'
import type { CanonicalEvent, CanonicalEventRevisionInput, EvidenceState, VideoSource } from '../types'
import GkCourtPicker from './GkCourtPicker'

type PlayerOption = { key: string; jersey: number; name: string; side: 'home' | 'away'; playerId: number | null }
type Props = {
  event: CanonicalEvent; source: VideoSource | null; currentTime: number; playable: boolean; clockUnverified: boolean; focusNotes?: boolean
  teams?: { home: { id: number; name: string }; away: { id: number; name: string } } | null; players?: PlayerOption[]
  onSave: (input: CanonicalEventRevisionInput) => void; onClose: () => void; saving?: boolean; error?: string
}
const states: EvidenceState[] = ['confirmed', 'no_visible', 'ambiguous', 'replay']

export default function EvidenceModal({ event, source, currentTime, playable, clockUnverified, focusNotes, teams = null, players = [], onSave, onClose, saving, error }: Props) {
  const payload = event.payload
  const [state, setState] = useState<EvidenceState>(payload.evidence_state)
  const [reason, setReason] = useState('Revisión de video')
  const [teamId, setTeamId] = useState<number | null>(payload.team_id)
  const [playerId, setPlayerId] = useState<number | null>(payload.player_id)
  const [goalkeeperId, setGoalkeeperId] = useState<number | null>(payload.goalkeeper_id ?? null)
  const [outcome, setOutcome] = useState(payload.outcome ?? '')
  const [note, setNote] = useState(payload.note ?? '')
  const [shotZone, setShotZone] = useState(payload.shot_zone ?? null)
  const activeVideo = source ? event.evidence?.find(item => item.kind === 'video' && item.video_source_id === source.id) : undefined
  const initialAnchor = activeVideo?.video_anchor_seconds ?? event.evidence?.find(item => item.kind === 'video')?.video_anchor_seconds
  const [videoSeconds, setVideoSeconds] = useState(String(initialAnchor ?? (playable ? currentTime : '')))
  const [videoChanged, setVideoChanged] = useState(false)
  const notesRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => { if (focusNotes) notesRef.current?.focus() }, [focusNotes])
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])
  const sideForTeam = teamId === teams?.home.id ? 'home' : teamId === teams?.away.id ? 'away' : null
  const teamPlayers = sideForTeam ? players.filter(player => player.side === sideForTeam) : players
  const opposingPlayers = sideForTeam ? players.filter(player => player.side !== sideForTeam) : []
  const evidence = () => {
    const anchor = videoSeconds.trim() === '' ? null : Number(videoSeconds)
    const existing = event.evidence?.map(({ kind, reference, scheduled_match_id, official_snapshot_id, video_source_id, video_anchor_seconds, uncertainty }) => ({ kind, reference, scheduled_match_id, official_snapshot_id, video_source_id, video_anchor_seconds, uncertainty })) ?? [{ kind: 'unavailable' as const, uncertainty: state === 'ambiguous' ? ['ambiguous_video'] : ['not_visible'] }]
    if (!videoChanged || !source || (anchor !== null && !Number.isFinite(anchor))) return existing
    const current = { kind: 'video' as const, reference: source.original_url, video_source_id: source.id, video_anchor_seconds: anchor, uncertainty: [] }
    const index = existing.findIndex(item => item.kind === 'video' && item.video_source_id === source.id)
    return index < 0 ? [...existing, current] : existing.map((item, itemIndex) => itemIndex === index ? current : item)
  }
  const allowedPlayerId = (value: number | null, options: PlayerOption[]) => value !== null && options.some(player => player.playerId === value) ? value : null
  const save = () => onSave({ ...payload, team_id: teams && [teams.home.id, teams.away.id].includes(teamId ?? 0) ? teamId : null, player_id: allowedPlayerId(playerId, teamPlayers), goalkeeper_id: payload.kind === 'shot' ? allowedPlayerId(goalkeeperId, opposingPlayers) : null, outcome: outcome || null, note: note || null, shot_zone: payload.kind === 'shot' ? shotZone : null, evidence_state: state, reason, evidence: evidence() })
  const playerSelect = (label: string, value: number | null, options: PlayerOption[], change: (value: number | null) => void) => <label className="block text-sm">{label}<select className="review-target mt-1 w-full rounded border p-2" value={value ?? ''} onChange={event => change(event.target.value ? Number(event.target.value) : null)}><option value="">Sin asignar</option>{options.filter(player => player.playerId !== null).map(player => <option key={player.key} value={player.playerId!}>#{player.jersey} {player.name}</option>)}</select></label>
  return <div className="fixed inset-0 z-20 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Editar incidencia">
    <div className="max-h-full w-full max-w-xl space-y-3 overflow-y-auto rounded bg-white p-4 shadow-xl"><div className="flex justify-between"><h2 className="font-semibold">Editar incidencia #{event.sequence}</h2><button className="review-target" onClick={onClose} aria-label="Cerrar">×</button></div>
      <p className="text-sm text-gray-600">La corrección crea una nueva revisión auditable; no modifica el registro original.</p>
      <div className="grid gap-2 sm:grid-cols-2"><label className="block text-sm">Equipo<select className="review-target mt-1 w-full rounded border p-2" value={teamId ?? ''} disabled={!teams} onChange={event => { const value = event.target.value ? Number(event.target.value) : null; setTeamId(value); setPlayerId(null); setGoalkeeperId(null) }}><option value="">Sin equipo</option>{teams && <><option value={teams.home.id}>{teams.home.name}</option><option value={teams.away.id}>{teams.away.name}</option></>}</select></label>{playerSelect(payload.kind === 'shot' ? 'Tirador' : 'Jugador', playerId, teamPlayers, setPlayerId)}</div>
      {payload.kind === 'shot' && <div className="grid gap-2 sm:grid-cols-2">{playerSelect('Arquero rival (opcional)', goalkeeperId, opposingPlayers, setGoalkeeperId)}<label className="block text-sm">Resultado<input className="review-target mt-1 w-full rounded border p-2" value={outcome} onChange={event => setOutcome(event.target.value)} /></label></div>}
      {payload.kind !== 'shot' && <label className="block text-sm">Resultado<input className="review-target mt-1 w-full rounded border p-2" value={outcome} onChange={event => setOutcome(event.target.value)} /></label>}
      <fieldset><legend className="text-sm font-medium">Estado de evidencia</legend><div className="grid grid-cols-2 gap-2">{states.map(value => <label key={value} className="review-target flex items-center rounded border p-2"><input className="min-h-4 min-w-4" type="radio" checked={state === value} onChange={() => setState(value)} /> <span className="ml-2">{value}</span></label>)}</div></fieldset>
      <label className="block text-sm">Marca de video (segundos, opcional)<input className="review-target mt-1 w-full rounded border p-2" type="number" min="0" step="0.1" value={videoSeconds} onChange={event => { setVideoChanged(true); setVideoSeconds(event.target.value) }} /></label>
      <p className="text-sm">{source ? `La evidencia queda vinculada a la fuente actual${playable ? ' y podés usar la posición reproducida o corregirla.' : '.'}` : 'Se conserva la evidencia existente; no hay fuente de video activa para reemplazarla.'}</p>
      {payload.kind === 'shot' && <fieldset><legend className="text-sm font-medium">Zona objetivo IHF (opcional)</legend><GkCourtPicker value={shotZone} onChange={setShotZone} /><button type="button" className="btn mt-1" onClick={() => setShotZone(null)}>Sin zona registrada</button></fieldset>}
      {clockUnverified && <p className="rounded bg-amber-100 p-2 text-sm" role="status">Tiempo de partido pendiente de confirmar: el video todavía no cubre un tramo reproducible del reloj.</p>}
      <label className="block text-sm">Notas<textarea className="review-target mt-1 w-full rounded border p-2" value={note} onChange={event => setNote(event.target.value)} /></label>
      <label className="block text-sm">Motivo de revisión<textarea ref={notesRef} className="review-target mt-1 w-full rounded border p-2" value={reason} onChange={event => setReason(event.target.value)} /></label>
      {error && <p role="alert" className="text-sm text-red-600">No se pudo guardar: {error}. El borrador se conserva; revisá el conflicto y corregilo antes de reintentar.</p>}
      <button className="btn btn-primary min-h-11 w-full" disabled={saving || !reason.trim()} onClick={save}>{saving ? 'Guardando…' : 'Guardar edición'}</button>
    </div>
  </div>
}
