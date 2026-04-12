import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Trash2, Plus, FileInput, Users } from 'lucide-react'
import { getMatches, createMatch, deleteMatch, getTeams, getTournaments, importPDF } from '../api/client'

export default function MatchesPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: matches = [], isLoading } = useQuery({ queryKey: ['matches'], queryFn: getMatches })
  const { data: teams = [] } = useQuery({ queryKey: ['teams'], queryFn: getTeams })
  const { data: tournaments = [] } = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments })

  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [homeId, setHomeId] = useState<number | ''>('')
  const [awayId, setAwayId] = useState<number | ''>('')
  const [tournamentId, setTournamentId] = useState<number | ''>('')

  const createMut = useMutation({
    mutationFn: () =>
      createMatch({
        date,
        home_team_id: homeId === '' ? null : homeId,
        away_team_id: awayId === '' ? null : awayId,
        tournament_id: tournamentId === '' ? null : tournamentId,
        youtube_link: null,
        main_team_focus: 'SAPA',
        venue: null, court: null, match_time: null, category_label: null,
        match_number_label: null, home_score: 0, away_score: 0, pdf_file_path: null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['matches'] }),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteMatch(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['matches'] }),
  })

  const importMut = useMutation({
    mutationFn: (file: File) => importPDF(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['matches'] }),
  })

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-4">
      <h1 className="text-2xl font-bold text-gray-900">Partidos</h1>

      <div className="card space-y-3">
        <h2 className="font-semibold text-gray-700">Nuevo partido</h2>
        <input type="date" className="w-full border rounded-xl px-3 py-2 text-sm" value={date} onChange={e => setDate(e.target.value)} />
        <select className="w-full border rounded-xl px-3 py-2 text-sm" value={homeId} onChange={e => setHomeId(e.target.value === '' ? '' : Number(e.target.value))}>
          <option value="">Equipo local…</option>
          {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select className="w-full border rounded-xl px-3 py-2 text-sm" value={awayId} onChange={e => setAwayId(e.target.value === '' ? '' : Number(e.target.value))}>
          <option value="">Equipo visitante…</option>
          {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select className="w-full border rounded-xl px-3 py-2 text-sm" value={tournamentId} onChange={e => setTournamentId(e.target.value === '' ? '' : Number(e.target.value))}>
          <option value="">Torneo (opcional)…</option>
          {tournaments.map(t => <option key={t.id} value={t.id}>{t.name} {t.year}</option>)}
        </select>
        <button onClick={() => createMut.mutate()} disabled={!date} className="btn btn-primary w-full py-2 gap-2 disabled:opacity-40">
          <Plus size={16} /> Crear partido
        </button>
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-700 mb-3">Importar planilla Femebal (PDF)</h2>
        <label className="btn btn-ghost w-full py-3 gap-2 cursor-pointer">
          <FileInput size={18} />
          {importMut.isPending ? 'Importando…' : 'Seleccionar PDF'}
          <input
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => e.target.files?.[0] && importMut.mutate(e.target.files[0])}
          />
        </label>
        {importMut.isSuccess && <p className="text-green-600 text-sm mt-2">Partido importado correctamente</p>}
        {importMut.isError && <p className="text-red-600 text-sm mt-2">Error al importar el PDF</p>}
      </div>

      {isLoading ? <p className="text-gray-400 text-sm">Cargando…</p> : (
        <ul className="space-y-2">
          {matches.map(m => (
            <li key={m.id} className="card flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold truncate">{m.home_team?.name ?? '?'} vs {m.away_team?.name ?? '?'}</p>
                <p className="text-sm text-gray-500">{m.date} · {m.home_score} - {m.away_score}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => navigate(`/match/${m.id}/squad`)} className="btn btn-ghost px-3 py-2 gap-1 text-sm">
                  <Users size={15} /> Plantel
                </button>
                <button onClick={() => navigate(`/match/${m.id}/live`)} className="btn btn-success px-3 py-2 gap-1 text-sm">
                  <Play size={15} /> Analizar
                </button>
                <button onClick={() => deleteMut.mutate(m.id)} className="text-red-400 hover:text-red-600 p-2">
                  <Trash2 size={18} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
