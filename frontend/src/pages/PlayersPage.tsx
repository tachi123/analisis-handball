import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, Plus } from 'lucide-react'
import { getPlayers, createPlayer, deletePlayer, getTeams } from '../api/client'

const POSITIONS = ['PV', 'CE', 'LI', 'LD', 'EXT', 'PI']

export default function PlayersPage() {
  const qc = useQueryClient()
  const { data: players = [], isLoading } = useQuery({ queryKey: ['players'], queryFn: () => getPlayers() })
  const { data: teams = [] } = useQuery({ queryKey: ['teams'], queryFn: getTeams })

  const [name, setName] = useState('')
  const [jersey, setJersey] = useState<number | ''>('')
  const [pos, setPos] = useState('')
  const [teamId, setTeamId] = useState<number | ''>('')

  const createMut = useMutation({
    mutationFn: () =>
      createPlayer({
        name,
        default_jersey_number: jersey === '' ? null : jersey,
        global_position: pos || null,
        team_id: teamId === '' ? null : teamId,
      }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['players'] }); setName(''); setJersey('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deletePlayer(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['players'] }),
  })

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-4">
      <h1 className="text-2xl font-bold text-gray-900">Plantel Global</h1>

      <div className="card space-y-3">
        <h2 className="font-semibold text-gray-700">Nuevo jugador</h2>
        <input className="w-full border rounded-xl px-3 py-2 text-sm" placeholder="Nombre completo" value={name} onChange={e => setName(e.target.value)} />
        <div className="flex gap-2">
          <input type="number" className="w-24 border rounded-xl px-3 py-2 text-sm" placeholder="Nº" value={jersey} onChange={e => setJersey(e.target.value === '' ? '' : Number(e.target.value))} />
          <select className="flex-1 border rounded-xl px-3 py-2 text-sm" value={pos} onChange={e => setPos(e.target.value)}>
            <option value="">Posición…</option>
            {POSITIONS.map(p => <option key={p}>{p}</option>)}
          </select>
        </div>
        <select className="w-full border rounded-xl px-3 py-2 text-sm" value={teamId} onChange={e => setTeamId(e.target.value === '' ? '' : Number(e.target.value))}>
          <option value="">Equipo (opcional)…</option>
          {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <button onClick={() => createMut.mutate()} disabled={!name} className="btn btn-primary w-full py-2 gap-2 disabled:opacity-40">
          <Plus size={16} /> Agregar jugador
        </button>
      </div>

      {isLoading ? <p className="text-gray-400 text-sm">Cargando…</p> : (
        <ul className="space-y-2">
          {players.map(p => (
            <li key={p.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold">{p.name}</p>
                <p className="text-sm text-gray-500">#{p.default_jersey_number ?? '—'} · {p.global_position ?? '—'} · {p.team?.name ?? '—'}</p>
              </div>
              <button onClick={() => deleteMut.mutate(p.id)} className="text-red-400 hover:text-red-600 p-2">
                <Trash2 size={18} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
