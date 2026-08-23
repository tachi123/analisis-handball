import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, RotateCcw, Save, Trash2 } from 'lucide-react'
import GkCourtPicker from '../components/GkCourtPicker'
import { createGoalkeeperShot, deleteGoalkeeperShot, getMatch, getSquad, listGoalkeeperShots } from '../api/client'
import type { GoalkeeperOutcome, GoalkeeperOriginZone, GoalkeeperShotType, GoalkeeperTargetZone } from '../types'

const SHOT_TYPE_OPTIONS: Array<{ value: GoalkeeperShotType; label: string }> = [
  { value: 'power', label: 'Fuerte' },
  { value: 'spin', label: 'Rosca' },
  { value: 'lob', label: 'Globo' },
]

const OUTCOME_OPTIONS: Array<{ value: GoalkeeperOutcome; label: string; selectedClass: string }> = [
  { value: 'goal', label: 'Gol', selectedClass: 'bg-red-600 text-white border-red-600' },
  { value: 'saved', label: 'Atajada', selectedClass: 'bg-green-600 text-white border-green-600' },
  { value: 'missed', label: 'Afuera', selectedClass: 'bg-gray-500 text-white border-gray-500' },
  { value: 'woodwork', label: 'Palo', selectedClass: 'bg-amber-500 text-white border-amber-500' },
  { value: 'blocked', label: 'Bloqueada', selectedClass: 'bg-blue-500 text-white border-blue-500' },
]

const ORIGIN_ORDER: GoalkeeperOriginZone[] = [
  '6m_left', '6m_center', '6m_right',
  '9m_left', '9m_center', '9m_right',
  'wing_left', 'wing_right', 'seven_meter', 'counter',
]

const ORIGIN_SHORT: Record<GoalkeeperOriginZone, string> = {
  '6m_left': '6m-I', '6m_center': '6m-C', '6m_right': '6m-D',
  '9m_left': '9m-I', '9m_center': '9m-C', '9m_right': '9m-D',
  wing_left: 'Ext-I', wing_right: 'Ext-D',
  seven_meter: '7m', counter: 'Contra',
}

const TARGET_SHORT: Record<GoalkeeperTargetZone, string> = {
  high_left: 'AI', high_center: 'AC', high_right: 'AD',
  low_left: 'BI', low_center: 'BC', low_right: 'BD',
}

const OUTCOME_BADGE: Record<Exclude<GoalkeeperOutcome, null>, string> = {
  goal: 'bg-red-100 text-red-700',
  saved: 'bg-green-100 text-green-700',
  missed: 'bg-gray-100 text-gray-600',
  woodwork: 'bg-amber-100 text-amber-700',
  blocked: 'bg-blue-100 text-blue-700',
}

const SHOT_TYPE_SHORT: Record<Exclude<GoalkeeperShotType, null>, string> = {
  power: 'F', spin: 'R', lob: 'G',
}

export default function GoalkeeperMode() {
  const qc = useQueryClient()
  const params = useParams()
  const matchId = Number(params.matchId)

  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null)
  const [labelInput, setLabelInput] = useState('')
  const [origin, setOrigin] = useState<GoalkeeperOriginZone | null>(null)
  const [target, setTarget] = useState<GoalkeeperTargetZone | null>(null)
  const [shotType, setShotType] = useState<GoalkeeperShotType | null>(null)
  const [outcome, setOutcome] = useState<GoalkeeperOutcome | null>(null)

  const { data: match, isLoading: matchLoading } = useQuery({
    queryKey: ['match', matchId],
    queryFn: () => getMatch(matchId),
  })
  const { data: squad = [] } = useQuery({ queryKey: ['squad', matchId], queryFn: () => getSquad(matchId) })
  const { data: shots = [] } = useQuery({
    queryKey: ['goalkeeper-shots', matchId],
    queryFn: () => listGoalkeeperShots(matchId),
  })

  const shooters = useMemo(() => squad.filter(sq => !sq.is_goalkeeper), [squad])

  const saveMut = useMutation({
    mutationFn: () =>
      createGoalkeeperShot(matchId, {
        shooter_player_id: selectedPlayerId,
        shooter_label: selectedPlayerId ? null : (labelInput.trim() || null),
        period: null,
        video_timestamp: null,
        origin_zone: origin,
        target_zone: target,
        shot_type: shotType,
        outcome,
        note: null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goalkeeper-shots', matchId] })
      setOrigin(null)
      setTarget(null)
      setShotType(null)
      setOutcome(null)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (shotId: number) => deleteGoalkeeperShot(matchId, shotId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['goalkeeper-shots', matchId] }),
  })

  const lastShotId = shots.length ? Math.max(...shots.map(s => s.id)) : null

  const summary = useMemo(() => {
    const goals = shots.filter(s => s.outcome === 'goal').length
    const saves = shots.filter(s => s.outcome === 'saved').length
    const denominator = saves + goals
    const originCounts: Partial<Record<GoalkeeperOriginZone, number>> = {}
    for (const shot of shots) {
      if (!shot.origin_zone) continue
      originCounts[shot.origin_zone] = (originCounts[shot.origin_zone] ?? 0) + 1
    }
    return {
      total: shots.length,
      goals,
      saves,
      savePct: denominator === 0 ? '—' : `${Math.round((saves / denominator) * 100)}%`,
      originCounts,
    }
  }, [shots])

  const newestFirst = useMemo(() => [...shots].reverse(), [shots])

  const selectShooter = (playerId: number) => {
    setSelectedPlayerId(current => (current === playerId ? null : playerId))
    setLabelInput('')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto space-y-4 p-4">
        <header className="card flex items-center gap-3">
          <Link to="/matches" className="btn btn-ghost p-2" aria-label="Volver a partidos">
            <ArrowLeft size={18} />
          </Link>
          <div className="min-w-0">
            <h1 className="font-bold truncate">
              {match ? `${match.home_team?.name ?? '?'} vs ${match.away_team?.name ?? '?'}` : 'Modo Arquero'}
            </h1>
            {match && <p className="text-sm text-gray-500">{match.date}</p>}
          </div>
        </header>

        {summary.total > 0 && (
          <section className="card">
            <div className="grid grid-cols-4 gap-2 text-center">
              <div>
                <p className="text-xl font-bold">{summary.total}</p>
                <p className="text-xs text-gray-500">Tiros</p>
              </div>
              <div>
                <p className="text-xl font-bold text-red-600">{summary.goals}</p>
                <p className="text-xs text-gray-500">Goles</p>
              </div>
              <div>
                <p className="text-xl font-bold text-green-600">{summary.saves}</p>
                <p className="text-xs text-gray-500">Atajadas</p>
              </div>
              <div>
                <p className="text-xl font-bold">{summary.savePct}</p>
                <p className="text-xs text-gray-500">% Atajadas</p>
              </div>
            </div>
            <p className="mt-3 flex flex-wrap gap-x-2 gap-y-1 text-xs text-gray-500">
              {ORIGIN_ORDER.filter(zone => (summary.originCounts[zone] ?? 0) > 0).map(zone => (
                <span key={zone} className="border rounded-lg px-2 py-0.5 bg-gray-50">
                  {ORIGIN_SHORT[zone]}: {summary.originCounts[zone]}
                </span>
              ))}
            </p>
          </section>
        )}

        {/* Fast logging panel */}
        <section className="card space-y-4">
          <div>
            <h2 className="font-semibold text-gray-700 mb-2">Lanzadora / Lanzador</h2>
            {shooters.length > 0 && (
              <div className="grid grid-cols-5 gap-2 mb-2">
                {shooters.map(sq => {
                  const isSelected = sq.player_id === selectedPlayerId
                  return (
                    <button
                      key={sq.player_id}
                      onClick={() => selectShooter(sq.player_id)}
                      className={`
                        flex flex-col items-center justify-center rounded-xl border-2 py-2 px-1
                        font-bold transition-all duration-100 select-none active:scale-95
                        ${isSelected ? 'bg-blue-600 border-blue-600 text-white ring-4 ring-blue-200' : 'bg-white border-gray-300 text-gray-800 hover:bg-gray-100'}
                      `}
                    >
                      <span className="text-xl leading-none">{sq.jersey_number}</span>
                      {sq.player?.name && (
                        <span className="text-[10px] mt-1 font-normal truncate max-w-full leading-tight opacity-80">
                          {sq.player.name.split(' ')[0]}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
            <input
              type="text"
              maxLength={16}
              placeholder="Nº desconocido (opcional)"
              className="w-full border rounded-xl px-3 py-2 text-sm"
              value={labelInput}
              onChange={e => {
                setSelectedPlayerId(null)
                setLabelInput(e.target.value)
              }}
            />
          </div>

          <div>
            <h2 className="font-semibold text-gray-700 mb-2">Zona de origen</h2>
            <GkCourtPicker value={origin} onChange={setOrigin} />
          </div>

          <div>
            <h2 className="font-semibold text-gray-700 mb-2">Destino del tiro</h2>
            <div className="space-y-1 max-w-xs mx-auto">
              {[['high', 'Arriba'], ['low', 'Abajo']].map(([row, rowLabel]) => (
                <div key={row} className="flex items-center gap-2">
                  <span className="w-14 text-xs text-gray-500 shrink-0">{rowLabel}</span>
                  <div className="grid grid-cols-3 gap-1 flex-1">
                    {(['left', 'center', 'right'] as const).map(col => {
                      const zone = `${row}_${col}` as GoalkeeperTargetZone
                      const isSelected = target === zone
                      return (
                        <button
                          key={zone}
                          onClick={() => setTarget(isSelected ? null : zone)}
                          className={`btn py-3 text-sm border ${isSelected ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-300 hover:bg-gray-100'}`}
                        >
                          {TARGET_SHORT[zone]}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-semibold text-gray-700 mb-2">Tipo de tiro</h2>
            <div className="flex gap-2">
              {SHOT_TYPE_OPTIONS.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setShotType(shotType === value ? null : value)}
                  className={`btn flex-1 py-2 text-sm border ${shotType === value ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-300 hover:bg-gray-100'}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h2 className="font-semibold text-gray-700 mb-2">Resultado</h2>
            <div className="grid grid-cols-5 gap-1.5">
              {OUTCOME_OPTIONS.map(({ value, label, selectedClass }) => (
                <button
                  key={value}
                  onClick={() => setOutcome(outcome === value ? null : value)}
                  className={`btn px-1 py-2 text-xs sm:text-sm border ${outcome === value ? selectedClass : 'bg-white border-gray-300 text-gray-800 hover:bg-gray-100'}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {saveMut.isError && <p className="text-red-600 text-sm">No se pudo registrar el tiro.</p>}
          <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="btn btn-success w-full py-4 text-lg gap-2 disabled:opacity-40">
            <Save size={20} /> Registrar tiro
          </button>
          <button
            onClick={() => lastShotId !== null && deleteMut.mutate(lastShotId)}
            disabled={lastShotId === null || deleteMut.isPending}
            className="btn btn-ghost w-full py-2 text-sm gap-2 disabled:opacity-40"
          >
            <RotateCcw size={15} /> Deshacer último
          </button>
          {deleteMut.isError && <p className="text-red-600 text-sm">No se pudo borrar el último tiro.</p>}
        </section>

        <section className="card">
          <h2 className="font-semibold text-gray-700 mb-2">Tiros registrados</h2>
          {newestFirst.length === 0 ? (
            <p className="text-sm text-gray-400">{matchLoading ? 'Cargando…' : 'Sin tiros registrados todavía.'}</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {newestFirst.map(shot => {
                const shooterSquad = squad.find(sq => sq.player_id === shot.shooter_player_id)
                const shooterText = shooterSquad
                  ? `#${shooterSquad.jersey_number}${shooterSquad.player?.name ? ` ${shooterSquad.player.name.split(' ')[0]}` : ''}`
                  : (shot.shooter_label || '—')
                return (
                  <li key={shot.id} className="flex items-center justify-between gap-2 py-2">
                    <span className="font-medium text-sm w-24 truncate shrink-0">{shooterText}</span>
                    <span className="text-sm text-gray-600 flex-1">
                      {shot.origin_zone ? ORIGIN_SHORT[shot.origin_zone] : '?'} → {shot.target_zone ? TARGET_SHORT[shot.target_zone] : '?'}
                      {shot.shot_type && (
                        <span className="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full bg-gray-100 text-[10px] font-bold text-gray-600 align-middle">
                          {SHOT_TYPE_SHORT[shot.shot_type]}
                        </span>
                      )}
                    </span>
                    {shot.outcome ? (
                      <span className={`text-xs font-semibold rounded-lg px-2 py-1 ${OUTCOME_BADGE[shot.outcome]}`}>
                        {OUTCOME_OPTIONS.find(o => o.value === shot.outcome)?.label}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">sin resultado</span>
                    )}
                    <button
                      onClick={() => deleteMut.mutate(shot.id)}
                      disabled={deleteMut.isPending}
                      className="text-red-400 hover:text-red-600 p-1 disabled:opacity-40"
                      aria-label={`Borrar tiro ${shot.id}`}
                    >
                      <Trash2 size={16} />
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
