import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Undo2, Timer, ArrowLeftRight, ChevronLeft, BarChart2, Users, Repeat2 } from 'lucide-react'
import { getMatch, getEvents, createEvent, deleteLastEvent, updateMatch } from '../api/client'
import { useTimer } from '../hooks/useTimer'
import { useTagging } from '../hooks/useTagging'
import ScoreBoard from '../components/ScoreBoard'
import PossessionBar from '../components/PossessionBar'
import PlayerGrid from '../components/PlayerGrid'
import TaggingWizard from '../components/TaggingWizard'
import type { TagState, MatchSquad } from '../types'

const ATTACK_PHASES = ['Posicional', 'Contraataque', 'Superioridad', 'Inferioridad', 'Portero-campo'] as const
type AttackPhase = (typeof ATTACK_PHASES)[number]

export default function MatchLive() {
  const { matchId } = useParams<{ matchId: string }>()
  const id = Number(matchId)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const timer = useTimer()

  const { data: match, isLoading } = useQuery({
    queryKey: ['match', id],
    queryFn: () => getMatch(id),
  })

  const { data: events = [] } = useQuery({
    queryKey: ['events', id],
    queryFn: () => getEvents(id),
  })

  const homeName = match?.home_team?.name ?? 'Local'
  const awayName = match?.away_team?.name ?? 'Visitante'

  const [possession, setPossession] = useState<string>(homeName)
  const [homeScore, setHomeScore] = useState(0)
  const [awayScore, setAwayScore] = useState(0)
  const [period, setPeriod] = useState<1 | 2>(1)
  const [attackPhase, setAttackPhase] = useState<AttackPhase>('Posicional')

  useEffect(() => {
    if (match) {
      setHomeScore(match.home_score)
      setAwayScore(match.away_score)
    }
  }, [match?.id])

  // Detectar portero activo del equipo contrario (para atajadas)
  const goalkeepers = useMemo(() => {
    if (!match) return { home: null as number | null, away: null as number | null }
    const homeGk = match.squad.find(
      (s: MatchSquad) => s.is_goalkeeper && match.home_team?.id != null &&
        s.player?.team_id === match.home_team.id
    )
    const awayGk = match.squad.find(
      (s: MatchSquad) => s.is_goalkeeper && match.away_team?.id != null &&
        s.player?.team_id === match.away_team.id
    )
    return {
      home: homeGk?.player_id ?? null,
      away: awayGk?.player_id ?? null,
    }
  }, [match])

  const tagging = useTagging(possession)

  const createEventMutation = useMutation({
    mutationFn: (state: TagState) => {
      // Auto-detect opposing goalkeeper on shot events
      let goalkeeperIdForEvent: number | null = null
      if (state.actionType === 'Lanzamiento' || state.actionType === '7 Metros') {
        const isHomeAttacking = possession === homeName
        goalkeeperIdForEvent = isHomeAttacking ? goalkeepers.away : goalkeepers.home
      }

      return createEvent(id, {
        match_id: id,
        game_timestamp: timer.elapsed,
        period,
        team_action: possession,
        player_id: state.playerId,
        action_type: state.actionType ?? '',
        result: state.result,
        shot_zone: state.shotZone,
        loss_detail: state.lossDetail,
        attack_phase: attackPhase,
        assist_player_id: state.assistPlayerId,
        goalkeeper_id: goalkeeperIdForEvent,
        sub_in_player_id: state.subInPlayerId,
        sub_out_player_id: state.subOutPlayerId,
        transition_type: null,
        transition_result: null,
        sanction_type: state.sanctionType,
        sanction_target: state.sanctionTarget,
      })
    },
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ['events', id] })
      if (saved.result === 'Gol' || saved.result === 'Gol (Arco Vacío)') {
        const isHome = possession === homeName
        const newHome = isHome ? homeScore + 1 : homeScore
        const newAway = !isHome ? awayScore + 1 : awayScore
        setHomeScore(newHome)
        setAwayScore(newAway)
        setPossession(p => (p === homeName ? awayName : homeName))
        updateMatch(id, { home_score: newHome, away_score: newAway })
          .then(() => qc.invalidateQueries({ queryKey: ['match', id] }))
      }
      if (saved.action_type === 'Pérdida') {
        setPossession(p => (p === homeName ? awayName : homeName))
      }
      tagging.reset()
    },
  })

  const undoMutation = useMutation({
    mutationFn: () => deleteLastEvent(id),
    onSuccess: (deleted) => {
      qc.invalidateQueries({ queryKey: ['events', id] })
      if (deleted.result === 'Gol' || deleted.result === 'Gol (Arco Vacío)') {
        const wasHome = deleted.team_action === homeName
        const newHome = wasHome ? Math.max(0, homeScore - 1) : homeScore
        const newAway = !wasHome ? Math.max(0, awayScore - 1) : awayScore
        setHomeScore(newHome)
        setAwayScore(newAway)
        updateMatch(id, { home_score: newHome, away_score: newAway })
          .then(() => qc.invalidateQueries({ queryKey: ['match', id] }))
      }
    },
  })

  const handleCommit = (state: TagState) => {
    createEventMutation.mutate(state)
  }

  if (isLoading || !match) {
    return <div className="flex items-center justify-center h-screen text-gray-500">Cargando partido…</div>
  }

  const recentEvents = [...events].reverse().slice(0, 8)

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top bar */}
      <div className="sticky top-0 z-20 bg-gray-50 px-3 pt-3 pb-2 space-y-2">
        {/* Nav strip */}
        <div className="flex items-center gap-2 pb-1">
          <button onClick={() => navigate('/matches')} className="text-gray-400 hover:text-gray-700 p-1">
            <ChevronLeft size={22} />
          </button>
          <span className="flex-1 text-sm font-semibold text-gray-700 truncate">
            {match?.home_team?.name ?? 'Local'} vs {match?.away_team?.name ?? 'Visitante'}
          </span>
          <button
            onClick={() => navigate(`/match/${id}/squad`)}
            className="text-gray-400 hover:text-gray-700 p-1"
            title="Gestionar plantel"
          >
            <Users size={20} />
          </button>
          <button
            onClick={() => navigate(`/match/${id}/stats`)}
            className="text-gray-400 hover:text-gray-700 p-1"
            title="Ver estadísticas"
          >
            <BarChart2 size={20} />
          </button>
        </div>
        <ScoreBoard
          timer={timer}
          homeTeam={homeName}
          awayTeam={awayName}
          homeScore={homeScore}
          awayScore={awayScore}
          period={period}
          onPeriodToggle={() => setPeriod(p => (p === 1 ? 2 : 1))}
          onHomeAdjust={(delta) => {
            const n = Math.max(0, homeScore + delta)
            setHomeScore(n)
            updateMatch(id, { home_score: n, away_score: awayScore })
          }}
          onAwayAdjust={(delta) => {
            const n = Math.max(0, awayScore + delta)
            setAwayScore(n)
            updateMatch(id, { home_score: homeScore, away_score: n })
          }}
        />
        <PossessionBar
          homeTeam={homeName}
          awayTeam={awayName}
          possession={possession}
          onSwitch={() => setPossession(p => (p === homeName ? awayName : homeName))}
        />

        {/* Attack phase selector */}
        <div className="flex gap-1 overflow-x-auto pb-1">
          {ATTACK_PHASES.map(phase => (
            <button
              key={phase}
              onClick={() => setAttackPhase(phase)}
              className={`shrink-0 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                attackPhase === phase
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {phase}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4 space-y-3 mt-2">
        {/* Quick controls */}
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => undoMutation.mutate()}
            disabled={events.length === 0 || undoMutation.isPending}
            className="btn btn-danger py-3 gap-2 disabled:opacity-40"
          >
            <Undo2 size={18} />
            Deshacer último
          </button>
          <button
            onClick={() =>
              createEvent(id, {
                match_id: id,
                game_timestamp: timer.elapsed,
                period,
                team_action: possession,
                player_id: null,
                action_type: 'Timeout',
                result: null,
                shot_zone: null,
                loss_detail: null,
                attack_phase: null,
                assist_player_id: null,
                goalkeeper_id: null,
                sub_in_player_id: null,
                sub_out_player_id: null,
                transition_type: null,
                transition_result: null,
                sanction_type: null,
                sanction_target: null,
              }).then(() => qc.invalidateQueries({ queryKey: ['events', id] }))
            }
            className="btn btn-warning py-3 gap-2"
          >
            <Timer size={18} />
            Timeout
          </button>
          <button
            onClick={() => tagging.startSubstitution()}
            className="btn btn-ghost py-3 gap-2"
          >
            <Repeat2 size={18} />
            Sustitución
          </button>
          <button
            onClick={() => setPossession(p => (p === homeName ? awayName : homeName))}
            className="btn btn-ghost py-3 gap-2"
          >
            <ArrowLeftRight size={18} />
            Cambiar
          </button>
        </div>

        {/* Player grid */}
        <div className="card">
          <p className="text-xs font-semibold text-gray-400 uppercase mb-2">
            {tagging.state.step === 'idle'
              ? 'Seleccionar jugador'
              : tagging.state.step === 'sub_out'
              ? '¿Quién SALE?'
              : tagging.state.step === 'sub_in'
              ? '¿Quién ENTRA?'
              : tagging.state.step === 'assist'
              ? '¿Quién asistió?'
              : 'Jugador seleccionado'}
          </p>
          <PlayerGrid
            squad={match.squad}
            selectedId={tagging.state.playerId}
            onSelect={(playerId) => {
              if (tagging.state.step === 'sub_out') {
                tagging.selectSubOut(playerId)
              } else if (tagging.state.step === 'sub_in') {
                const finalState = tagging.selectSubIn(playerId)
                handleCommit(finalState)
              } else if (tagging.state.step === 'assist') {
                const finalState = tagging.selectAssist(playerId)
                handleCommit(finalState)
              } else {
                tagging.selectPlayer(playerId)
              }
            }}
          />
          {/* Skip assist button */}
          {tagging.state.step === 'assist' && (
            <button
              onClick={() => {
                const finalState = tagging.selectAssist(null)
                handleCommit(finalState)
              }}
              className="btn btn-ghost w-full mt-2 py-2 text-sm"
            >
              Sin asistencia
            </button>
          )}
        </div>

        {/* Wizard */}
        {tagging.state.step !== 'idle' && tagging.state.step !== 'sub_out' && tagging.state.step !== 'sub_in' && tagging.state.step !== 'assist' && (
          <div className="card space-y-3">
            <TaggingWizard tagging={tagging} onCommit={handleCommit} />
            <button
              onClick={tagging.reset}
              className="btn btn-ghost w-full py-2 text-sm"
            >
              Cancelar
            </button>
          </div>
        )}

        {/* Recent events */}
        {recentEvents.length > 0 && (
          <div className="card">
            <p className="text-xs font-semibold text-gray-400 uppercase mb-2">Últimos eventos</p>
            <ul className="space-y-1">
              {recentEvents.map(ev => {
                const mins = Math.floor(ev.game_timestamp / 60).toString().padStart(2, '0')
                const secs = Math.floor(ev.game_timestamp % 60).toString().padStart(2, '0')
                const phaseTag = ev.attack_phase ? ` · ${ev.attack_phase}` : ''
                const assistTag = ev.assist_player ? ` (asist: ${ev.assist_player.name.split(' ')[0]})` : ''
                const subTag = ev.action_type === 'Sustitución' && ev.sub_out_player && ev.sub_in_player
                  ? ` ${ev.sub_out_player.name.split(' ')[0]} → ${ev.sub_in_player.name.split(' ')[0]}`
                  : ''
                return (
                  <li key={ev.id} className="flex items-center gap-2 text-sm py-1 border-b border-gray-50 last:border-0">
                    <span className="font-mono text-gray-400 text-xs w-10">{mins}:{secs}</span>
                    <span className="font-semibold text-gray-700">{ev.player?.name.split(' ')[0] ?? '—'}</span>
                    <span className="text-gray-600 truncate flex-1">
                      {ev.action_type}{subTag}{phaseTag}{assistTag}
                    </span>
                    {ev.result && (
                      <span className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded-full ${
                        ev.result === 'Gol' || ev.result === 'Gol (Arco Vacío)'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {ev.result}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
