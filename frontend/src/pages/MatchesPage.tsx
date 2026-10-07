import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { createMatch, getFixtures, getMatches, getTeams, getTournaments } from '../api/client'

function errorMessage(reason: any) {
  const detail = reason?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => item?.msg ?? String(item)).join(' ')
  if (detail && typeof detail === 'object') return detail.msg ?? 'No se pudo crear el partido.'
  return 'No se pudo crear el partido.'
}

export default function MatchesPage() {
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ home_team_id: '', away_team_id: '', tournament_id: '', date: '', match_time: '' })
  const fixtures = useQuery({ queryKey: ['fixtures'], queryFn: () => getFixtures('all') })
  const matches = useQuery({ queryKey: ['matches'], queryFn: getMatches })
  const teams = useQuery({ queryKey: ['teams'], queryFn: getTeams })
  const tournaments = useQuery({ queryKey: ['tournaments'], queryFn: getTournaments })
  const create = useMutation({
    mutationFn: () => createMatch({
      home_team_id: Number(form.home_team_id), away_team_id: Number(form.away_team_id),
      tournament_id: form.tournament_id ? Number(form.tournament_id) : null,
      date: form.date || null, match_time: form.match_time || null,
    } as never),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['matches'] }); setOpen(false); setError('') },
    onError: (reason: unknown) => setError(errorMessage(reason)),
  })
  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!form.home_team_id || !form.away_team_id) return setError('Seleccioná ambos equipos.')
    if (form.home_team_id === form.away_team_id) return setError('Local y visitante deben ser equipos distintos.')
    create.mutate()
  }
  const manual = (matches.data ?? []).filter((match: any) => !match.scheduled_match_id && match.origin === 'manual')
  return <main className="max-w-4xl mx-auto space-y-5 p-4">
    <header className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold">Partidos</h1><p className="text-sm text-gray-500">Fixtures importados y partidos creados para análisis.</p></div><button className="btn btn-primary" onClick={() => setOpen(!open)}>{open ? 'Cerrar' : 'Crear partido manual'}</button></header>
    {open && <form className="card grid gap-3 sm:grid-cols-2" onSubmit={submit} noValidate><h2 className="sm:col-span-2 font-semibold">Nuevo partido manual</h2><label>Equipo local<select aria-label="Equipo local" className="mt-1 w-full border rounded p-2" value={form.home_team_id} onChange={e => setForm({ ...form, home_team_id: e.target.value })}><option value="">Seleccionar</option>{(teams.data ?? []).map(team => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label><label>Equipo visitante<select aria-label="Equipo visitante" className="mt-1 w-full border rounded p-2" value={form.away_team_id} onChange={e => setForm({ ...form, away_team_id: e.target.value })}><option value="">Seleccionar</option>{(teams.data ?? []).map(team => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label><label>Fecha (opcional)<input aria-label="Fecha" type="date" className="mt-1 w-full border rounded p-2" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} /></label><label>Hora (opcional)<input aria-label="Hora" type="time" className="mt-1 w-full border rounded p-2" value={form.match_time} onChange={e => setForm({ ...form, match_time: e.target.value })} /></label><label className="sm:col-span-2">Torneo legado (clasificación opcional)<select aria-label="Torneo opcional" className="mt-1 w-full border rounded p-2" value={form.tournament_id} onChange={e => setForm({ ...form, tournament_id: e.target.value })}><option value="">Sin torneo</option>{(tournaments.data ?? []).map(t => <option key={t.id} value={t.id}>{t.name} · {t.year}</option>)}</select></label>{error && <p role="alert" className="sm:col-span-2 text-sm text-red-700">{error}</p>}<button className="btn btn-primary sm:col-span-2" disabled={create.isPending}>{create.isPending ? 'Creando…' : 'Crear y cargar planilla'}</button></form>}
    <section className="card space-y-2"><h2 className="font-semibold">Fixtures importados</h2>{(fixtures.data ?? []).map(fixture => <article key={fixture.fixture_key} className="border rounded p-3 flex justify-between gap-2"><div><b>{fixture.home_registration.display_name} vs {fixture.away_registration.display_name}</b><p className="text-sm text-gray-500">Fixture importado · {fixture.scheduled_date ?? 'Sin fecha'} · {fixture.stage.name}</p></div><Link className="btn" to={fixture.roster_status === 'not_confirmed' ? `/fixtures/${fixture.fixture_key}/review` : `/fixtures/${fixture.fixture_key}`}>{fixture.roster_status === 'not_confirmed' ? 'Revisar PDF' : 'Preparar análisis'}</Link></article>)}</section>
    <section className="card space-y-2"><h2 className="font-semibold">Partidos manuales</h2>{manual.length === 0 ? <p className="text-sm text-gray-500">No hay partidos manuales.</p> : manual.map((match: any) => <article key={match.id} className="border rounded p-3 flex justify-between gap-2"><div><b>{match.home_team?.name} vs {match.away_team?.name}</b><p className="text-sm text-gray-500">Partido manual · {match.date ?? 'Sin fecha'} · {match.tournament?.name ?? 'Sin torneo'}</p></div><Link className="btn btn-primary" to={`/matches/${match.id}/prepare`}>Preparar planilla</Link></article>)}</section>
  </main>
}
