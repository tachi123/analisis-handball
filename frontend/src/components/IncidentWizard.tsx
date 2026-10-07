import { useState } from 'react'
import { X, MoveUp, MoveDown, Minus, Circle, Target, Ban, UserMinus, UserPlus, ShieldAlert, Flag, Timer } from 'lucide-react'
import type { CanonicalEventCommand, ShotZone, CanonicalEventKind } from '../types'

type WizardStep = 'category' | 'shot' | 'turnover' | 'foul' | 'gk' | 'team'

interface PlayerOption {
  key: string
  jersey: number
  name: string
  side: 'home' | 'away'
  playerId: number | null
}

interface Props {
  isOpen: boolean
  onClose: () => void
  onSubmit: (command: CanonicalEventCommand) => void
  submitting: boolean
  period: number
  regulationSeconds: number | null
  clockUnverified: boolean
  teamId: number | null
  homeTeam: { id: number; name: string } | null
  awayTeam: { id: number; name: string } | null
  officialHomePlayers: PlayerOption[]
  officialAwayPlayers: PlayerOption[]
  hasVideo: boolean
  currentVideoTime: number
  videoSourceId: number | null
  videoUrl: string | null
}

const SHOT_ZONES: { value: ShotZone; label: string }[] = [
  { value: 1, label: 'Zona 1: Extremo izq.' },
  { value: 2, label: 'Zona 2: Lateral izq.' },
  { value: 3, label: 'Zona 3: Central 9m' },
  { value: 4, label: 'Zona 4: Lateral der.' },
  { value: 5, label: 'Zona 5: Extremo der.' },
  { value: 6, label: 'Zona 6: Pivote 6m' },
  { value: 7, label: 'Zona 7: 7 metros' },
  { value: 8, label: 'Zona 8: Contraataque' },
  { value: 9, label: 'Zona 9: Otro' },
]

const TURNOVER_REASONS = [
  { value: 'bad_pass', label: 'Mal pase', icon: MoveDown },
  { value: 'bad_reception', label: 'Mala recepción', icon: MoveDown },
  { value: 'walking', label: 'Caminar (pasos)', icon: MoveUp },
  { value: 'double_dribble', label: 'Doble bote', icon: Minus },
  { value: 'offensive_foul', label: 'Falta en ataque', icon: ShieldAlert },
  { value: 'steal', label: 'Intercepción / Robo', icon: UserPlus },
  { value: 'three_seconds', label: '3 segundos', icon: Timer },
  { value: 'area_violation', label: 'Pisar el área', icon: Ban },
  { value: 'technical', label: 'Otro error técnico', icon: Ban },
]

const FOUL_TYPES = [
  { value: 'two_minute_exclusion', label: '2 minutos', icon: Timer, color: 'bg-amber-100 text-amber-800', borderColor: 'amber' },
  { value: 'yellow_card', label: 'Amarilla', icon: Flag, color: 'bg-yellow-100 text-yellow-800', borderColor: 'yellow' },
  { value: 'red_card', label: 'Roja', icon: Ban, color: 'bg-red-100 text-red-800', borderColor: 'red' },
  { value: 'blue_card', label: 'Azul', icon: ShieldAlert, color: 'bg-blue-100 text-blue-800', borderColor: 'blue' },
  { value: 'seven_meter', label: '7 metros', icon: Target, color: 'bg-purple-100 text-purple-800', borderColor: 'purple' },
]

const SHOT_OUTCOMES = [
  { value: 'goal', label: 'GOL', color: 'bg-green-100 text-green-800', borderColor: 'green', icon: Target },
  { value: 'save', label: 'ATAJADA', color: 'bg-blue-100 text-blue-800', borderColor: 'blue', icon: ShieldAlert },
  { value: 'woodwork', label: 'PALO', color: 'bg-amber-100 text-amber-800', borderColor: 'amber', icon: Minus },
  { value: 'miss', label: 'AFUERA', color: 'bg-gray-100 text-gray-800', borderColor: 'gray', icon: X },
  { value: 'blocked', label: 'BLOQUEADO', color: 'bg-purple-100 text-purple-800', borderColor: 'purple', icon: Ban },
]

const GK_OUTCOMES = [
  { value: 'active', label: 'Arquero activo', color: 'bg-blue-100 text-blue-800', borderColor: 'blue', icon: ShieldAlert },
  { value: 'unknown', label: 'Arquero desconocido', color: 'bg-gray-100 text-gray-800', borderColor: 'gray', icon: Target },
]

const TEAM_EVENTS = [
  { value: 'kickoff', kind: 'other' as CanonicalEventKind, label: 'Saque inicial / Inicio período', icon: Circle },
  { value: 'period_end', kind: 'other' as CanonicalEventKind, label: 'Fin de período', icon: Timer },
  { value: 'timeout', kind: 'other' as CanonicalEventKind, label: 'Time-out', icon: Timer },
  { value: 'substitution', kind: 'lineup_change' as CanonicalEventKind, label: 'Sustitución', icon: UserMinus },
]

function submitButtonLabel(submitting: boolean, outcome: string | null | undefined): string {
  if (submitting) return 'Registrando…'
  if (outcome === 'goal') return 'Registrar GOL'
  return `Registrar ${outcome ?? ''}`
}

function foulButtonLabel(outcome: string | null | undefined): string {
  if (!outcome) return ''
  return `Registrar ${outcome.replace('_', ' ')}`
}

function turnoverButtonLabel(submitting: boolean, outcome: string | null | undefined): string {
  if (submitting) return 'Registrando…'
  if (!outcome) return ''
  return `Registrar ${outcome.replace('_', ' ')}`
}

function teamButtonLabel(submitting: boolean, outcome: string | null | undefined): string {
  if (submitting) return 'Registrando…'
  if (!outcome) return ''
  return `Registrar ${outcome.replace('_', ' ')}`
}

function shotOutcomeClass(outcome: typeof SHOT_OUTCOMES[0], selected: boolean): string {
  const stateClass = selected
    ? 'border-indigo-600 ring-2 ring-indigo-200 shadow-sm'
    : 'border-transparent hover:border-gray-300'
  return `p-3 rounded-xl border-2 text-center transition-all ${outcome.color} ${stateClass}`
}

function foulTypeClass(_foul: typeof FOUL_TYPES[0], _selected: boolean): string {
  return ''
}

function gkOutcomeClass(_outcome: typeof GK_OUTCOMES[0], _selected: boolean): string {
  return ''
}

function teamEventClass(_item: { value: string }, selected: boolean): string {
  if (selected) return 'p-3 rounded-xl border-2 text-left transition-all bg-indigo-100 border-indigo-600'
  return 'p-3 rounded-xl border-2 text-left transition-all bg-white border-gray-200 hover:border-indigo-300'
}

function shotZoneClass(_zone: typeof SHOT_ZONES[0], selected: boolean): string {
  if (selected) return 'p-3 rounded-xl border-2 text-center transition-all bg-indigo-100 border-indigo-600'
  return 'p-3 rounded-xl border-2 text-center transition-all bg-white border-gray-200 hover:border-indigo-300'
}

function turnoverReasonClass(_reason: typeof TURNOVER_REASONS[0], selected: boolean): string {
  if (selected) return 'p-3 rounded-xl border-2 text-left transition-all bg-amber-100 border-amber-600'
  return 'p-3 rounded-xl border-2 text-left transition-all bg-white border-gray-200 hover:border-amber-300'
}

function categoryButtonClass(item: { color: string }, _selected: boolean): string {
  return `relative p-4 rounded-xl border-2 text-left transition-all hover:shadow-md ${item.color}`
}

export default function IncidentWizard({
  isOpen,
  onClose,
  onSubmit,
  submitting,
  period,
  regulationSeconds,
  clockUnverified,
  teamId,
  homeTeam,
  awayTeam,
  officialHomePlayers,
  officialAwayPlayers,
  hasVideo,
  currentVideoTime,
  videoSourceId,
  videoUrl,
}: Props) {
  const [step, setStep] = useState<WizardStep>('category')
  const [formData, setFormData] = useState<Partial<CanonicalEventCommand>>({
    kind: undefined,
    period,
    regulation_seconds: regulationSeconds,
    clock_unverified: clockUnverified,
    team_id: teamId,
    player_id: null,
    related_player_id: null,
    goalkeeper_id: null,
    outcome: null,
    shot_zone: null,
    fact_kind: 'observed',
    evidence_state: hasVideo ? 'confirmed' : 'no_visible',
    uncertainty: clockUnverified ? ['clock_unverified'] : [],
    note: '',
    evidence: hasVideo && videoSourceId ? [{
      kind: 'video' as const,
      reference: videoUrl,
      video_source_id: videoSourceId,
      video_anchor_seconds: currentVideoTime,
      uncertainty: [],
    }] : [{ kind: 'unavailable' as const, uncertainty: ['not_visible'] }],
  })

  if (!isOpen) return null

  const allPlayers = [...officialHomePlayers, ...officialAwayPlayers]
  const selectedTeamId = formData.team_id ?? null
  const teamPlayers = selectedTeamId
    ? allPlayers.filter(p => (selectedTeamId === homeTeam?.id && p.side === 'home') || (selectedTeamId === awayTeam?.id && p.side === 'away'))
    : allPlayers

  const updateForm = (updates: Partial<CanonicalEventCommand>) => {
    setFormData(prev => ({ ...prev, ...updates }))
  }

  const selectTeam = (nextTeamId: number | null) => {
    setFormData(prev => nextTeamId === prev.team_id ? prev : {
      ...prev,
      team_id: nextTeamId,
      // Player roles are team-scoped; never carry a prior team's IDs into a new command.
      player_id: null,
      related_player_id: null,
      goalkeeper_id: null,
    })
  }

  const handleCategorySelect = (kind: CanonicalEventKind) => {
    // Categories reuse the primary player only where it still denotes an actor.
    updateForm({ kind, outcome: null, related_player_id: null, goalkeeper_id: null, shot_zone: null,
      player_id: kind === 'other' ? null : formData.player_id ?? null })
    setStep(kind === 'shot' ? 'shot' : kind === 'turnover' || kind === 'recovery' ? 'turnover' : kind === 'foul_sanction' ? 'foul' : kind === 'goalkeeper_change' ? 'gk' : 'team')
  }

  const handleSubmit = () => {
    if (!formData.kind) return
    if (formData.team_id === null) {
      alert('Seleccioná un equipo primero')
      return
    }
    onSubmit(formData as CanonicalEventCommand)
    onClose()
  }

  const renderCategoryGrid = () => (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {[
        { kind: 'shot' as CanonicalEventKind, label: 'Tiro al arco', icon: Target, desc: 'Gol, atajada, palo, afuera, bloqueado', color: 'bg-green-50 border-green-200' },
        { kind: 'turnover' as CanonicalEventKind, label: 'Pérdida / Cambio posesión', icon: MoveDown, desc: 'Mal pase, pasos, doble, falta ataque, robo', color: 'bg-amber-50 border-amber-200' },
        { kind: 'foul_sanction' as CanonicalEventKind, label: 'Falta / Sanción', icon: ShieldAlert, desc: '2 min, amarilla, roja, azul, 7 metros', color: 'bg-red-50 border-red-200' },
        { kind: 'goalkeeper_change' as CanonicalEventKind, label: 'Estado de arquero', icon: UserPlus, desc: 'Arquero activo o desconocido', color: 'bg-purple-50 border-purple-200' },
        { kind: 'recovery' as CanonicalEventKind, label: 'Recuperación', icon: MoveUp, desc: 'Balón recuperado tras pérdida rival', color: 'bg-indigo-50 border-indigo-200' },
        { kind: 'lineup_change' as CanonicalEventKind, label: 'Cambio / Tiempo', icon: Timer, desc: 'Sustitución, time-out, cambio arquero', color: 'bg-gray-50 border-gray-200' },
        { kind: 'other' as CanonicalEventKind, label: 'Otro', icon: Circle, desc: 'Saque inicial, fin período, evento genérico', color: 'bg-slate-50 border-slate-200' },
      ].map(item => (
        <button
          key={item.kind}
          className={categoryButtonClass(item, false)}
          onClick={() => handleCategorySelect(item.kind)}
          disabled={submitting}
        >
          <div className="flex items-center gap-3">
            <item.icon className="w-8 h-8 text-indigo-600" />
            <div>
              <p className="font-semibold text-gray-900">{item.label}</p>
              <p className="text-xs text-gray-600">{item.desc}</p>
            </div>
          </div>
          <span className="absolute bottom-2 right-2 text-xs text-gray-400">{item.kind}</span>
        </button>
      ))}
    </div>
  )

  const renderPlayerSelector = (label: string, currentId: number | null, onChange: (id: number | null) => void, filterSide?: 'home' | 'away') => {
    const players = filterSide
      ? allPlayers.filter(p => p.side === filterSide)
      : teamPlayers
    const selectValue = currentId !== null ? String(currentId) : ''
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">{label}</label>
        <select
          className="w-full rounded-xl border p-3 text-sm bg-white"
          value={selectValue}
          onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— Sin jugador (solo equipo) —</option>
          {players.map(p => (
            <option key={p.key} value={p.playerId !== null ? String(p.playerId) : ''}>
              #{p.jersey} {p.name} {p.playerId ? '✓' : '(sin ID)'}
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500">
          {filterSide ? 'Jugadores de la planilla oficial' : selectedTeamId ? `Jugadores de ${selectedTeamId === homeTeam?.id ? homeTeam?.name : awayTeam?.name}` : 'Todos los jugadores importados'}
        </p>
      </div>
    )
  }

  const renderShotStep = () => (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
      <h3 className="font-semibold text-lg flex items-center gap-2"><Target className="w-5 h-5 text-green-600" /> Tiro al arco</h3>
      
      <div className="grid gap-3 sm:grid-cols-5">
        {SHOT_OUTCOMES.map(o => (
          <button
            key={o.value}
            className={shotOutcomeClass(o, formData.outcome === o.value)}
            onClick={() => updateForm({ outcome: o.value })}
            disabled={submitting}
            aria-pressed={formData.outcome === o.value}
          >
            <o.icon className="w-5 h-5 mx-auto mb-1" />
            <p className="font-semibold text-sm">{o.label}</p>
          </button>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {SHOT_ZONES.map(z => (
          <button
            key={z.value}
            className={shotZoneClass(z, formData.shot_zone === z.value)}
            onClick={() => updateForm({ shot_zone: z.value })}
            disabled={submitting}
          >
            <p className="font-medium text-xs">{z.label}</p>
          </button>
        ))}
      </div>

      {renderPlayerSelector('Tirador', formData.player_id as number | null, id => updateForm({ player_id: id }))}
      {renderPlayerSelector('Asistente (opcional)', formData.related_player_id as number | null, id => updateForm({ related_player_id: id }))}
      {renderPlayerSelector('Arquero rival (opcional)', formData.goalkeeper_id as number | null, id => updateForm({ goalkeeper_id: id }), selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'away' : 'home') : undefined)}

      <div className="flex gap-2 pt-2">
        <button className="btn flex-1" onClick={handleSubmit} disabled={submitting || !formData.outcome}>
          {foulButtonLabel(formData.outcome)}
        </button>
        <button className="btn btn-secondary" onClick={() => { setStep('category'); updateForm({ outcome: null, player_id: null, related_player_id: null }) }}>Volver</button>
      </div>
    </div>
  )

  const renderTurnoverStep = () => (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
      <h3 className="font-semibold text-lg flex items-center gap-2"><MoveDown className="w-5 h-5 text-amber-600" /> Pérdida / Cambio de posesión</h3>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {TURNOVER_REASONS.map(r => (
          <button
            key={r.value}
            className={turnoverReasonClass(r, formData.outcome === r.value)}
            onClick={() => updateForm({ outcome: r.value, kind: formData.kind === 'recovery' ? 'recovery' : 'turnover' })}
            disabled={submitting}
          >
            <r.icon className="w-5 h-5 text-amber-600 mr-2" />
            <span className="font-medium text-sm">{r.label}</span>
          </button>
        ))}
      </div>

      <p className="text-sm text-gray-600">
        {formData.kind === 'recovery'
          ? '¿Quién recuperó el balón? (opcional: quién lo perdió antes)'
          : '¿Quién perdió el balón? (opcional: quién lo recuperó)'}
      </p>

      {renderPlayerSelector(
        formData.kind === 'recovery' ? 'Jugador que recupera' : 'Jugador que pierde',
        formData.player_id as number | null,
        id => updateForm({ player_id: id }),
         selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'home' : 'away') : undefined
      )}

      {renderPlayerSelector(
        formData.kind === 'recovery' ? 'Jugador que perdió (opcional)' : 'Jugador rival que recupera (opcional)',
        formData.related_player_id as number | null,
        id => updateForm({ related_player_id: id }),
         selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'away' : 'home') : undefined
      )}

      <div className="flex gap-2 pt-2">
        <button className="btn flex-1" onClick={handleSubmit} disabled={submitting || !formData.outcome}>
          {turnoverButtonLabel(submitting, formData.outcome)}
        </button>
        <button className="btn btn-secondary" onClick={() => { setStep('category'); updateForm({ outcome: null, player_id: null, related_player_id: null }) }}>Volver</button>
      </div>
    </div>
  )

  const renderFoulStep = () => (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
      <h3 className="font-semibold text-lg flex items-center gap-2"><ShieldAlert className="w-5 h-5 text-red-600" /> Falta / Sanción</h3>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {FOUL_TYPES.map(f => (
          <button
            key={f.value}
            className={foulTypeClass(f, formData.outcome === f.value)}
            onClick={() => updateForm({ outcome: f.value })}
            disabled={submitting}
          >
            <f.icon className="w-5 h-5 mx-auto mb-1" />
            <p className="font-semibold text-sm">{f.label}</p>
          </button>
        ))}
      </div>

       {renderPlayerSelector('Infractor', formData.player_id as number | null, id => updateForm({ player_id: id }), selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'home' : 'away') : undefined)}
       {renderPlayerSelector('Jugador afectado (opcional)', formData.related_player_id as number | null, id => updateForm({ related_player_id: id }), selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'away' : 'home') : undefined)}

      <div className="flex gap-2 pt-2">
        <button className="btn flex-1" onClick={handleSubmit} disabled={submitting || !formData.outcome}>
          {foulButtonLabel(formData.outcome)}
        </button>
        <button className="btn btn-secondary" onClick={() => { setStep('category'); updateForm({ outcome: null, player_id: null, related_player_id: null }) }}>Volver</button>
      </div>
    </div>
  )

  const renderGKStep = () => (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
      <h3 className="font-semibold text-lg flex items-center gap-2"><UserPlus className="w-5 h-5 text-purple-600" /> Estado de arquero</h3>

      <div className="grid gap-3 sm:grid-cols-2">
        {GK_OUTCOMES.map(o => (
          <button
            key={o.value}
            className={gkOutcomeClass(o, formData.outcome === o.value)}
            onClick={() => updateForm({ outcome: o.value })}
            disabled={submitting}
          >
            <o.icon className="w-6 h-6 mx-auto mb-2" />
            <p className="font-semibold">{o.label}</p>
          </button>
        ))}
      </div>

       {renderPlayerSelector('Arquero', formData.player_id as number | null, id => updateForm({ player_id: id }), selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'home' : 'away') : undefined)}

      <div className="flex gap-2 pt-2">
        <button className="btn flex-1" onClick={handleSubmit} disabled={submitting || !formData.outcome}>
          {submitButtonLabel(submitting, formData.outcome)}
        </button>
        <button className="btn btn-secondary" onClick={() => { setStep('category'); updateForm({ outcome: null, player_id: null }) }}>Volver</button>
      </div>
    </div>
  )

  const renderTeamStep = () => (
    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
      <h3 className="font-semibold text-lg flex items-center gap-2"><Circle className="w-5 h-5 text-gray-600" /> Evento de equipo</h3>

      <div className="grid gap-2 sm:grid-cols-2">
        {TEAM_EVENTS.map(item => (
          <button
            key={item.value}
            className={teamEventClass(item, formData.outcome === item.value)}
            onClick={() => updateForm(item.value === 'substitution'
              ? { kind: item.kind, outcome: item.value, goalkeeper_id: null, shot_zone: null }
              : { kind: item.kind, outcome: item.value, player_id: null, related_player_id: null, goalkeeper_id: null, shot_zone: null })}
            disabled={submitting}
          >
            <item.icon className="w-5 h-5 text-indigo-600 mr-2" />
            <span className="font-medium text-sm">{item.label}</span>
          </button>
        ))}
      </div>

      {formData.outcome === 'substitution' && (
        <>
           {renderPlayerSelector('Sale', formData.related_player_id as number | null, id => updateForm({ related_player_id: id }), selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'home' : 'away') : undefined)}
           {renderPlayerSelector('Entra', formData.player_id as number | null, id => updateForm({ player_id: id }), selectedTeamId ? (selectedTeamId === homeTeam?.id ? 'home' : 'away') : undefined)}
        </>
      )}

      <div className="flex gap-2 pt-2">
        <button className="btn flex-1" onClick={handleSubmit} disabled={submitting || !formData.outcome}>
          {teamButtonLabel(submitting, formData.outcome)}
        </button>
        <button className="btn btn-secondary" onClick={() => { setStep('category'); updateForm({ outcome: null, player_id: null, related_player_id: null }) }}>Volver</button>
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Registrar incidente">
      <div className="w-full max-w-2xl max-h-[90vh] bg-white rounded-2xl shadow-xl overflow-hidden">
        <header className="flex items-center justify-between p-4 border-b sticky top-0 bg-white z-10">
          <h2 className="text-xl font-bold">Registrar incidente</h2>
          <button className="p-2 rounded-lg hover:bg-gray-100" onClick={onClose} aria-label="Cerrar"><X className="w-5 h-5" /></button>
        </header>

        <div className="p-4 space-y-4 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Team selector (always visible) */}
          <div className="rounded-xl border p-3 bg-gray-50">
            <p className="text-sm font-medium text-gray-700 mb-2">Equipo</p>
            <div className="flex flex-wrap gap-2">
               <button className={`btn ${selectedTeamId === homeTeam?.id ? 'btn-primary' : ''}`} onClick={() => selectTeam(homeTeam?.id ?? null)}>{homeTeam?.name ?? 'Local'}</button>
               <button className={`btn ${selectedTeamId === awayTeam?.id ? 'btn-primary' : ''}`} onClick={() => selectTeam(awayTeam?.id ?? null)}>{awayTeam?.name ?? 'Visitante'}</button>
               <button className={`btn ${selectedTeamId === null ? 'btn-primary' : ''}`} onClick={() => selectTeam(null)}>Equipo no visible</button>
            </div>
             {selectedTeamId === null && <p className="text-xs text-red-600 mt-1">Seleccioná un equipo para continuar</p>}
          </div>

          {/* Match clock display */}
          <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-3 text-center">
            <p className="text-xs text-indigo-700">Reloj de partido</p>
            <p className="font-mono text-2xl font-bold text-indigo-900">
              {regulationSeconds === null ? '00:00' : `${String(Math.floor(regulationSeconds / 60)).padStart(2, '0')}:${String(regulationSeconds % 60).padStart(2, '0')}`}
            </p>
            {clockUnverified && <span className="text-xs text-amber-700">⚠ Reloj sin verificar</span>}
          </div>

          {step === 'category' && renderCategoryGrid()}
          {step === 'shot' && renderShotStep()}
          {step === 'turnover' && renderTurnoverStep()}
          {step === 'foul' && renderFoulStep()}
          {step === 'gk' && renderGKStep()}
          {step === 'team' && renderTeamStep()}
        </div>
      </div>
    </div>
  )
}
