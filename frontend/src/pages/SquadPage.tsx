import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, UserPlus, Trash2, Shield, Play } from 'lucide-react'
import { getMatch, getPlayers, upsertSquadPlayer, removeSquadPlayer } from '../api/client'

export default function SquadPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const id = Number(matchId)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { data: match, isLoading } = useQuery({
    queryKey: ['match', id],
    queryFn: () => getMatch(id),
  })

  const { data: allPlayers = [] } = useQuery({
    queryKey: ['players'],
    queryFn: () => getPlayers(),
  })

  const squadPlayerIds = new Set(match?.squad.map(s => s.player_id) ?? [])

  // Jugadores de los equipos del partido que aún no están en el plantel
  const availablePlayers = allPlayers.filter(p => {
    const inTeam = p.team_id === match?.home_team_id || p.team_id === match?.away_team_id
    return inTeam && !squadPlayerIds.has(p.id)
  })

  const upsertMut = useMutation({
    mutationFn: (data: { player_id: number; jersey_number: number; is_goalkeeper: boolean }) =>
      upsertSquadPlayer(id, {
        ...data,
        match_id: id,
        official_goals: 0,
        official_yellow: 0,
        official_2min: 0,
        official_red: 0,
        official_blue: 0,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['match', id] }),
  })

  const removeMut = useMutation({
    mutationFn: (playerId: number) => removeSquadPlayer(id, playerId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['match', id] }),
  })

  const [addingId, setAddingId] = useState<number | null>(null)
  const [jersey, setJersey] = useState('')
  const [isGK, setIsGK] = useState(false)

  const handleAdd = (playerId: number) => {
    const num = parseInt(jersey)
    if (!jersey || isNaN(num)) return
    upsertMut.mutate({ player_id: playerId, jersey_number: num, is_goalkeeper: isGK })
    setAddingId(null)
    setJersey('')
    setIsGK(false)
  }

  if (isLoading || !match) {
    return <div className="flex items-center justify-center h-screen text-gray-400">Cargando…</div>
  }

  const homeName = match.home_team?.name ?? 'Local'
  const awayName = match.away_team?.name ?? 'Visitante'
  const sortedSquad = [...match.squad].sort((a, b) => a.jersey_number - b.jersey_number)

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/matches')} className="text-gray-400 hover:text-gray-700 p-1">
          <ChevronLeft size={24} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-gray-900 truncate">Plantel del partido</h1>
          <p className="text-sm text-gray-500 truncate">{homeName} vs {awayName} · {match.date}</p>
        </div>
        <button
          onClick={() => navigate(`/match/${id}/live`)}
          className="btn btn-primary px-4 py-2 gap-2 shrink-0"
        >
          <Play size={16} /> Analizar
        </button>
      </div>

      {/* Plantel actual */}
      <div className="card">
        <h2 className="font-semibold text-gray-700 mb-3">
          Plantel ({match.squad.length} jugadores)
        </h2>
        {sortedSquad.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-6">
            Sin jugadores. Agregá desde abajo.
          </p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {sortedSquad.map(sq => (
              <li key={sq.id} className="flex items-center gap-3 py-2.5">
                <span className="w-9 h-9 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm shrink-0">
                  {sq.jersey_number}
                </span>
                <span className="flex-1 text-sm font-medium text-gray-800 truncate">
                  {sq.player?.name ?? '—'}
                </span>
                {sq.is_goalkeeper && (
                  <Shield size={14} className="text-yellow-500 shrink-0" />
                )}
                <span className="text-xs text-gray-400 shrink-0">
                  {sq.player?.global_position ?? ''}
                </span>
                <button
                  onClick={() => removeMut.mutate(sq.player_id)}
                  disabled={removeMut.isPending}
                  className="text-red-400 hover:text-red-600 p-1 shrink-0"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Agregar jugadores */}
      <div className="card">
        <h2 className="font-semibold text-gray-700 mb-3">Agregar jugadores</h2>
        {availablePlayers.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-6">
            {allPlayers.filter(p => p.team_id === match.home_team_id || p.team_id === match.away_team_id).length === 0
              ? 'No hay jugadores registrados para estos equipos. Creá jugadores en la sección Plantel.'
              : 'Todos los jugadores del plantel ya están agregados.'}
          </p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {availablePlayers.map(p => (
              <li key={p.id} className="py-2.5">
                {addingId === p.id ? (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-gray-800 flex-1 min-w-0 truncate">
                      {p.name}
                    </span>
                    <input
                      type="number"
                      placeholder="Nro."
                      className="w-16 border rounded-lg px-2 py-1.5 text-sm text-center"
                      value={jersey}
                      onChange={e => setJersey(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleAdd(p.id)}
                      autoFocus
                      min={1}
                      max={99}
                    />
                    <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isGK}
                        onChange={e => setIsGK(e.target.checked)}
                        className="rounded"
                      />
                      Portero
                    </label>
                    <button
                      onClick={() => handleAdd(p.id)}
                      disabled={!jersey || upsertMut.isPending}
                      className="btn btn-primary px-3 py-1.5 text-sm disabled:opacity-40"
                    >
                      OK
                    </button>
                    <button
                      onClick={() => { setAddingId(null); setJersey('') }}
                      className="text-gray-400 hover:text-gray-600 p-1"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3">
                    <span className="flex-1 text-sm text-gray-700 truncate">{p.name}</span>
                    <span className="text-xs text-gray-400 shrink-0">
                      {p.default_jersey_number ? `#${p.default_jersey_number}` : ''} {p.global_position ?? ''}
                    </span>
                    <button
                      onClick={() => {
                        setAddingId(p.id)
                        setJersey(p.default_jersey_number?.toString() ?? '')
                        setIsGK(p.global_position === 'PV')
                      }}
                      className="btn btn-ghost px-3 py-1.5 text-sm gap-1 shrink-0"
                    >
                      <UserPlus size={14} /> Agregar
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
