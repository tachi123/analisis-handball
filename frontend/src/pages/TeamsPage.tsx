import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, Plus } from 'lucide-react'
import { getTeams, createTeam, deleteTeam } from '../api/client'

export default function TeamsPage() {
  const qc = useQueryClient()
  const { data = [], isLoading } = useQuery({ queryKey: ['teams'], queryFn: getTeams })
  const [name, setName] = useState('')
  const [club, setClub] = useState('')
  const [category, setCategory] = useState('')

  const createMut = useMutation({
    mutationFn: () => createTeam({ name, club_name: club || null, category: category || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['teams'] }); setName(''); setClub(''); setCategory('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteTeam(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['teams'] }),
  })

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-4">
      <h1 className="text-2xl font-bold text-gray-900">Equipos</h1>

      <div className="card space-y-3">
        <h2 className="font-semibold text-gray-700">Nuevo equipo</h2>
        <input className="w-full border rounded-xl px-3 py-2 text-sm" placeholder="Nombre del equipo" value={name} onChange={e => setName(e.target.value)} />
        <input className="w-full border rounded-xl px-3 py-2 text-sm" placeholder="Club (ej: SAPA)" value={club} onChange={e => setClub(e.target.value)} />
        <input className="w-full border rounded-xl px-3 py-2 text-sm" placeholder="Categoría (ej: Mayores Fem)" value={category} onChange={e => setCategory(e.target.value)} />
        <button onClick={() => createMut.mutate()} disabled={!name} className="btn btn-primary w-full py-2 gap-2 disabled:opacity-40">
          <Plus size={16} /> Crear equipo
        </button>
      </div>

      {isLoading ? <p className="text-gray-400 text-sm">Cargando…</p> : (
        <ul className="space-y-2">
          {data.map(t => (
            <li key={t.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold">{t.name}</p>
                <p className="text-sm text-gray-500">{t.club_name} · {t.category}</p>
              </div>
              <button onClick={() => deleteMut.mutate(t.id)} className="text-red-400 hover:text-red-600 p-2">
                <Trash2 size={18} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
