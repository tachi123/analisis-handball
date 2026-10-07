import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getFixtureRoster, resolveFixtureRoster } from '../api/client'

export default function FixtureRosterPage() {
  const { fixtureKey = '' } = useParams()
  const navigate = useNavigate(); const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['fixture-roster', fixtureKey], queryFn: () => getFixtureRoster(fixtureKey), enabled: Boolean(fixtureKey) })
  const [choices, setChoices] = useState<Record<number, number | 'create'>>({})
  const resolveMutation = useMutation({ mutationFn: () => resolveFixtureRoster(fixtureKey, data!.players.filter(player => player.player_id === null).map((player) => {
    const choice = choices[player.id]
    return typeof choice === 'number'
      ? { snapshot_player_id: player.id, existing_player_id: choice, create_player: false }
      : { snapshot_player_id: player.id, create_player: true }
  })), onSuccess: (result) => { queryClient.invalidateQueries({ queryKey: ['fixtures'] }); queryClient.invalidateQueries({ queryKey: ['fixture-roster', fixtureKey] }); if (result.roster_status === 'ready') navigate(`/fixtures/${fixtureKey}`) } })
  if (isLoading || !data) return <main className="p-4">Cargando planilla…</main>
  const unresolved = data.players.filter(player => player.player_id === null)
  const complete = unresolved.every(player => choices[player.id] !== undefined)
  return <main className="max-w-2xl mx-auto space-y-5 p-4"><header><Link className="text-sm underline" to="/matches">← Partidos</Link><h1 className="text-2xl font-bold">Resolver identidades de planilla</h1><p className="text-sm text-gray-600">{data.fixture.home_registration.display_name} vs {data.fixture.away_registration.display_name}. Cada vínculo es una decisión explícita: no se fusionan identidades automáticamente.</p></header><section className="card space-y-3">{data.players.map(player => <div key={player.id} className="border-b pb-3 last:border-0"><p className="font-medium">{player.side === 'home' ? 'Local' : 'Visitante'} · #{player.jersey_number} {player.name}</p>{player.player_id ? <p className="text-sm text-green-700">Identidad vinculada</p> : <select aria-label={`Identidad ${player.id}`} className="mt-2 w-full border rounded-xl px-3 py-2" value={choices[player.id] ?? ''} onChange={event => setChoices({ ...choices, [player.id]: event.target.value === 'create' ? 'create' : Number(event.target.value) })}><option value="">Elegí una decisión</option><option value="create">Crear identidad nueva desde esta planilla</option>{player.candidates.map(candidate => <option key={candidate.id} value={candidate.id}>Vincular con {candidate.name} #{candidate.default_jersey_number ?? '?'}</option>)}</select>}</div>)}</section><button className="btn btn-primary w-full" disabled={!complete || resolveMutation.isPending} onClick={() => resolveMutation.mutate()}>{resolveMutation.isPending ? 'Guardando…' : 'Guardar plantel y volver a la preparación'}</button>{resolveMutation.isError && <p className="text-sm text-red-600">No se pudo guardar. Revisá que cada decisión siga siendo válida.</p>}</main>
}
