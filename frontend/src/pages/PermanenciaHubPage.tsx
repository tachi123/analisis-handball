import { useMemo, useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ClipboardCheck, MapPin, PlayCircle, Video } from 'lucide-react'
import { getFixtures, getStandings, getPlayerStatistics, getClubStatistics } from '../api/client'
import type { ScheduledFixture, StandingsResponse, PlayerStatisticsResponse, ClubStatisticsResponse } from '../types'

function resultLabel(fixture: ScheduledFixture) {
  if (fixture.result_status === 'approved') return 'Resultado oficial'
  if (fixture.result_status === 'reported') return 'Resultado informado'
  if (fixture.result_status === 'disputed') return 'Resultado en revisión'
  return 'Programado'
}

function score(fixture: ScheduledFixture) {
  return fixture.source_home_score === null || fixture.source_away_score === null
    ? 'vs'
    : `${fixture.source_home_score} – ${fixture.source_away_score}`
}

export default function PermanenciaHubPage() {
  const fixturesQuery = useQuery({ queryKey: ['fixtures'], queryFn: () => getFixtures('all') })
  const [round, setRound] = useState('all')
  const [team, setTeam] = useState('all')
  const [standings, setStandings] = useState<StandingsResponse | null>(null)
  const standingsStageId = 9
  const [playerStats, setPlayerStats] = useState<PlayerStatisticsResponse | null>(null)
  const [clubStats, setClubStats] = useState<ClubStatisticsResponse | null>(null)
  const permanencia = useMemo(
    () => (fixturesQuery.data ?? []).filter(fixture => fixture.stage.name === 'Torneo Permanencia 2026 3ªM'),
    [fixturesQuery.data],
  )
  const rounds = [...new Set(permanencia.map(fixture => fixture.round_number))].sort((a, b) => a - b)
  const teams = [...new Set(permanencia.flatMap(fixture => [fixture.home_registration.display_name, fixture.away_registration.display_name]))].sort()

  // Fetch standings when components mounts or when fixtures data changes
  useEffect(() => {
    getStandings(standingsStageId).then(setStandings).catch(console.error)
  }, [fixturesQuery.data, getStandings])

  // Fetch player and club statistics
  useEffect(() => {
    getPlayerStatistics(standingsStageId).then(setPlayerStats).catch(console.error)
    getClubStatistics(standingsStageId).then(setClubStats).catch(console.error)
  }, [getPlayerStatistics, getClubStatistics])

  const shown = permanencia.filter(fixture =>
    (round === 'all' || fixture.round_number === Number(round)) &&
    (team === 'all' || fixture.home_registration.display_name === team || fixture.away_registration.display_name === team),
  ).sort((left, right) =>
    (left.scheduled_date ?? '9999-12-31').localeCompare(right.scheduled_date ?? '9999-12-31') ||
    left.round_number - right.round_number ||
    (left.match_time ?? '').localeCompare(right.match_time ?? ''),
  )

  if (fixturesQuery.isLoading) return <main className="max-w-6xl mx-auto p-4">Cargando Permanencia…</main>
  if (fixturesQuery.isError) return <main className="max-w-6xl mx-auto p-4 text-red-700" role="alert">No se pudo cargar el fixture de Permanencia.</main>

  return <main className="max-w-6xl mx-auto space-y-5 p-4">
    <header className="space-y-1">
      <p className="text-sm font-semibold text-blue-700">FEMEBAL 2026 · Mayores 3ª Masculino</p>
      <h1 className="text-3xl font-bold tracking-tight">Torneo Permanencia</h1>
      <p className="text-sm text-gray-600">Fixture, resultados y evidencia disponible para navegar cada partido.</p>
    </header>

    {standings && (
      <section className="card p-4 mb-4">
        <h2 className="text-xl font-bold mb-3">Tabla de Posiciones</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm border border-gray-200 rounded-lg">
            <thead className="bg-gray-100 text-xs uppercase text-gray-600">
              <tr>
                <th className="px-3 py-3">Pos</th>
                <th className="px-3 py-3">Equipo</th>
                <th className="px-3 py-3">PJ</th>
                <th className="px-3 py-3">G</th>
                <th className="px-3 py-3">E</th>
                <th className="px-3 py-3">P</th>
                <th className="px-3 py-3">CP</th>
                <th className="px-3 py-3">GF</th>
                <th className="px-3 py-3">GC</th>
                <th className="px-3 py-3">Dif</th>
                <th className="px-3 py-3">Pts</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {standings.teams.map((team) => (
                <tr key={team.team_id} className="hover:bg-gray-50">
                  <td className="px-3 py-3 font-medium">{team.pos}</td>
                  <td className="px-3 py-3">{team.name}</td>
                  <td className="px-3 py-3">{team.pj}</td>
                  <td className="px-3 py-3">{team.wins}</td>
                  <td className="px-3 py-3">{team.draws}</td>
                  <td className="px-3 py-3">{team.losses}</td>
                  <td className="px-3 py-3">{team.cp}</td>
                  <td className="px-3 py-3">{team.gf}</td>
                  <td className="px-3 py-3">{team.ga}</td>
                  <td className="px-3 py-3">{team.gd}</td>
                  <td className="px-3 py-3 font-bold">{team.pts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-gray-600">{standings.note}</p>
      </section>
    )}

    {/* --- Player statistics table --- */}
    {playerStats && (
      <section className="card p-4 mb-4">
        <h2 className="text-xl font-bold mb-3">Estadísticas por Jugador</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm border border-gray-200 rounded-lg">
            <thead className="bg-gray-100 text-xs uppercase text-gray-600">
              <tr>
                <th className="px-3 py-3">Jugador</th>
                <th className="px-3 py-3">Club</th>
                <th className="px-3 py-3">Partidos</th>
                <th className="px-3 py-3">Goles</th>
                <th className="px-3 py-3">Amarillas</th>
                <th className="px-3 py-3">2min</th>
                <th className="px-3 py-3">Rojas</th>
                <th className="px-3 py-3">Azules</th>
                <th className="px-3 py-3">Promedio</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {playerStats.rows.map((row, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-3 py-3 font-medium">{row.name}</td>
                  <td className="px-3 py-3">{row.club}</td>
                  <td className="px-3 py-3">{row.appearances}</td>
                  <td className="px-3 py-3">{row.goals}</td>
                  <td className="px-3 py-3">{row.yellow}</td>
                  <td className="px-3 py-3">{row.two_min}</td>
                  <td className="px-3 py-3">{row.red}</td>
                  <td className="px-3 py-3">{row.blue}</td>
                  <td className="px-3 py-3 font-medium">{row.goals_per_game}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-gray-600">{playerStats.note}</p>
      </section>
    )}

    {/* --- Club statistics table --- */}
    {clubStats && (
      <section className="card p-4 mb-4">
        <h2 className="text-xl font-bold mb-3">Estadísticas por Club</h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm border border-gray-200 rounded-lg">
            <thead className="bg-gray-100 text-xs uppercase text-gray-600">
              <tr>
                <th className="px-3 py-3">Club</th>
                <th className="px-3 py-3">Partidos</th>
                <th className="px-3 py-3">Goles</th>
                <th className="px-3 py-3">Amarillas</th>
                <th className="px-3 py-3">2min</th>
                <th className="px-3 py-3">Rojas</th>
                <th className="px-3 py-3">Azules</th>
                <th className="px-3 py-3">Jugadores</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {clubStats.rows.map((row, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-3 py-3 font-medium">{row.club}</td>
                  <td className="px-3 py-3">{row.appearances}</td>
                  <td className="px-3 py-3">{row.goals}</td>
                  <td className="px-3 py-3">{row.yellow}</td>
                  <td className="px-3 py-3">{row.two_min}</td>
                  <td className="px-3 py-3">{row.red}</td>
                  <td className="px-3 py-3">{row.blue}</td>
                  <td className="px-3 py-3 font-medium">{row.distinct_players}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-sm text-gray-600">{clubStats.note}</p>
      </section>
    )}

    <section className="card grid gap-3 sm:grid-cols-2" aria-label="Filtros del fixture">
      <label className="text-sm font-medium">Fecha<select className="mt-1 w-full rounded border p-2" value={round} onChange={event => setRound(event.target.value)}><option value="all">Todas las fechas</option>{rounds.map(number => <option key={number} value={number}>Fecha {number}</option>)}</select></label>
      <label className="text-sm font-medium">Equipo<select className="mt-1 w-full rounded border p-2" value={team} onChange={event => setTeam(event.target.value)}><option value="all">Todos los equipos</option>{teams.map(name => <option key={name} value={name}>{name}</option>)}</select></label>
    </section>

    <p className="text-sm text-gray-600">{shown.length} de {permanencia.length} partidos</p>
    <section className="hidden overflow-x-auto rounded-xl border bg-white md:block" aria-label="Tabla de partidos de Permanencia">
      <table className="w-full min-w-[1050px] text-left text-sm"><thead className="bg-gray-100 text-xs uppercase text-gray-600"><tr><th className="px-3 py-3">Fecha</th><th className="px-3 py-3">Partido</th><th className="px-3 py-3">Resultado</th><th className="px-3 py-3">Sede / árbitros</th><th className="px-3 py-3">Evidencia</th><th className="px-3 py-3">Acción</th></tr></thead><tbody className="divide-y">{shown.map(fixture => <tr key={fixture.fixture_key} className="align-top hover:bg-blue-50"><td className="whitespace-nowrap px-3 py-3 font-medium">F{fixture.round_number}<br /><span className="font-normal text-gray-600">{fixture.scheduled_date ?? 'Sin fecha'}<br />{fixture.match_time ?? 'Hora pendiente'}</span></td><td className="px-3 py-3 font-semibold">{fixture.home_registration.display_name}<br />{fixture.away_registration.display_name}</td><td className="px-3 py-3"><b className="text-base text-blue-700">{score(fixture)}</b><br /><span className="text-xs text-gray-600">{resultLabel(fixture)}</span></td><td className="max-w-56 px-3 py-3 text-xs text-gray-600">{fixture.venue ?? 'Sede pendiente'}{fixture.referees && <><br />Árbitros: {fixture.referees}</>}</td><td className="px-3 py-3"><div className="flex flex-wrap gap-1 text-xs"><span className={`rounded-full px-2 py-1 ${fixture.official_snapshot_id ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>Planilla {fixture.official_snapshot_id ? 'oficial' : 'pendiente'}</span><span className={`rounded-full px-2 py-1 ${fixture.has_video ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'}`}>Video {fixture.has_video ? 'sí' : 'no'}</span><span className={`rounded-full px-2 py-1 ${fixture.analysis_run_count ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}>Análisis {fixture.analysis_run_count || '—'}</span></div></td><td className="px-3 py-3"><div className="flex flex-col items-start gap-2">{fixture.linked_match_id && <Link className="btn btn-primary" to={`/match/${fixture.linked_match_id}/review`}>Abrir análisis</Link>}{fixture.has_video && fixture.youtube_link && <a className="btn" href={fixture.youtube_link} target="_blank" rel="noreferrer">Ver video</a>}{fixture.official_snapshot_id && <Link className="btn" to={`/fixtures/${fixture.fixture_key}`}>Ver planilla</Link>}</div></td></tr>)}</tbody></table>
    </section>
    <section className="grid gap-3 md:hidden" aria-label="Partidos de Permanencia">
      {shown.map(fixture => <article key={fixture.fixture_key} className="card space-y-3 border-l-4 border-l-blue-600">
        <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-gray-500">Fecha {fixture.round_number} · {fixture.scheduled_date ?? 'Sin fecha'} {fixture.match_time ? `· ${fixture.match_time}` : ''}</p><h2 className="mt-1 text-lg font-bold">{fixture.home_registration.display_name} <span className="text-blue-700">{score(fixture)}</span> {fixture.away_registration.display_name}</h2></div><span className={`rounded-full px-2 py-1 text-xs font-semibold ${fixture.result_status === 'approved' ? 'bg-green-100 text-green-800' : fixture.result_status === 'reported' ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-700'}`}>{resultLabel(fixture)}</span></div>
        <div className="space-y-1 text-sm text-gray-600">{fixture.venue && <p className="flex gap-1"><MapPin size={16} aria-hidden="true" />{fixture.venue}{fixture.court ? ` · ${fixture.court}` : ''}</p>}{fixture.referees && <p>Árbitros: {fixture.referees}</p>}</div>
        <div className="flex flex-wrap gap-2 text-xs font-medium"><span className={`rounded-full px-2 py-1 ${fixture.official_snapshot_id ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>Planilla {fixture.official_snapshot_id ? 'oficial' : 'pendiente'}</span><span className={`rounded-full px-2 py-1 ${fixture.has_video ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'}`}>Video {fixture.has_video ? 'disponible' : 'sin registrar'}</span><span className={`rounded-full px-2 py-1 ${fixture.analysis_run_count ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}>Análisis {fixture.analysis_run_count ? `${fixture.analysis_run_count} disponible${fixture.analysis_run_count > 1 ? 's' : ''}` : 'pendiente'}</span></div>
        <div className="flex flex-wrap gap-2">{fixture.linked_match_id && <Link className="btn btn-primary" to={`/match/${fixture.linked_match_id}/review`}><PlayCircle size={16} />Abrir análisis</Link>}{fixture.has_video && fixture.youtube_link && <a className="btn" href={fixture.youtube_link} target="_blank" rel="noreferrer"><Video size={16} />Ver video</a>}{fixture.official_snapshot_id && <Link className="btn" to={`/fixtures/${fixture.fixture_key}`}><ClipboardCheck size={16} />Ver planilla</Link>}</div>
      </article>)}
    </section>
    {!shown.length && <p className="card text-sm text-gray-600">No hay partidos con esos filtros.</p>}
  </main>
}
