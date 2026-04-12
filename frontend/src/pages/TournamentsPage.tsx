import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, Plus } from 'lucide-react'
import { getTournaments, createTournament, deleteTournament } from '../api/client'

export default function TournamentsPage() {
  const qc = useQueryClient()
  const { data = [], isLoading } = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments })
  const [name, setName] = useState('')
  const [category, setCategory] = useState('')
  const [year, setYear] = useState(new Date().getFullYear())

  const createMut = useMutation({
    mutationFn: () => createTournament({ name, category, year }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['tournaments'] }); setName(''); setCategory('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteTournament(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tournaments'] }),
  })

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-4">
      <h1 className="text-2xl font-bold text-gray-900">Torneos</h1>

      <div className="card space-y-3">
        <h2 className="font-semibold text-gray-700">Nuevo torneo</h2>
        <input className="w-full border rounded-xl px-3 py-2 text-sm" placeholder="Nombre" value={name} onChange={e => setName(e.target.value)} />
        <input className="w-full border rounded-xl px-3 py-2 text-sm" placeholder="Categoría (ej: Mayores, Juniors)" value={category} onChange={e => setCategory(e.target.value)} />
        <input className="w-full border rounded-xl px-3 py-2 text-sm" type="number" placeholder="Año" value={year} onChange={e => setYear(Number(e.target.value))} />
        <button onClick={() => createMut.mutate()} disabled={!name || !category} className="btn btn-primary w-full py-2 gap-2 disabled:opacity-40">
          <Plus size={16} /> Crear torneo
        </button>
      </div>

      {isLoading ? <p className="text-gray-400 text-sm">Cargando…</p> : (
        <ul className="space-y-2">
          {data.map(t => (
            <li key={t.id} className="card flex items-center justify-between">
              <div>
                <p className="font-semibold">{t.name}</p>
                <p className="text-sm text-gray-500">{t.category} · {t.year}</p>
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
