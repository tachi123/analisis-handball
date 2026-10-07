import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, ChevronLeft } from 'lucide-react'
import { reviewFixturePDF, confirmFixtureReview } from '../api/client'
import type { FixturePreviewResult, FixtureConfirmation } from '../types'

export default function FixtureReviewPage() {
  const { fixtureKey = '' } = useParams()
  const navigate = useNavigate()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['fixture-review', fixtureKey],
    queryFn: () => reviewFixturePDF(fixtureKey),
    enabled: Boolean(fixtureKey),
  })

  const confirmMutation = useMutation({
    mutationFn: (confirmation: FixtureConfirmation) => confirmFixtureReview(fixtureKey, confirmation),
    onSuccess: () => navigate(`/fixtures/${fixtureKey}/roster`),
  })

  if (isLoading) {
    return <main className="p-4">Cargando vista previa…</main>
  }

  if (isError) {
    const axiosError = error as { response?: { data?: { detail?: string } } }
    const message = axiosError.response?.data?.detail || 'No se pudo cargar la vista previa'
    return (
      <main className="max-w-4xl mx-auto p-4">
        <div className="card p-4 text-center">
          <p className="text-red-600">Error: {message}</p>
          <Link className="btn btn-ghost mt-4" to="/matches">
            <ChevronLeft size={16} /> Volver a partidos
          </Link>
        </div>
      </main>
    )
  }

  if (!data) {
    return <main className="p-4">Sin datos de vista previa</main>
  }

  const { fixture, preview, home_compatibility, away_compatibility, score_reconciliation } = data

  const getCompatibilityBadge = (status: FixturePreviewResult['home_compatibility']['status']) => {
    switch (status) {
      case 'compatible':
        return { className: 'bg-green-100 text-green-800', label: 'Compatible' }
      case 'incompatible':
        return { className: 'bg-red-100 text-red-800', label: 'Incompatible' }
      case 'unresolved':
      default:
        return { className: 'bg-amber-100 text-amber-800', label: 'Sin resolver' }
    }
  }

  const getScoreBadge = (status: FixturePreviewResult['score_reconciliation']) => {
    switch (status) {
      case 'match':
        return { className: 'bg-green-100 text-green-800', label: 'Marcador coincide' }
      case 'mismatch':
        return { className: 'bg-red-100 text-red-800', label: 'Marcador no coincide' }
      case 'unknown':
      default:
        return { className: 'bg-gray-100 text-gray-800', label: 'Marcador desconocido' }
    }
  }

  const homeBadge = getCompatibilityBadge(home_compatibility.status)
  const awayBadge = getCompatibilityBadge(away_compatibility.status)
  const scoreBadge = getScoreBadge(score_reconciliation)

  const isCompatible = home_compatibility.status !== 'incompatible' && away_compatibility.status !== 'incompatible'

  const buildConfirmation = (): FixtureConfirmation => {
    const toConfirmedPlayer = (player: FixturePreviewResult['preview']['home_team']['players'][number]) => ({
      name: player.name,
      jersey_number: player.number,
      official_goals: player.goals,
      official_yellow: player.yellow,
      official_2min: player.two_min,
      official_red: player.red,
      official_blue: player.blue,
    })

    return {
      home_team_id: fixture.home_registration.id,
      away_team_id: fixture.away_registration.id,
      // Player identities are intentionally resolved in the following roster step.
      home_players: preview.home_team.players.map(toConfirmedPlayer),
      away_players: preview.away_team.players.map(toConfirmedPlayer),
      acknowledge_score_mismatch: score_reconciliation === 'mismatch',
    }
  }

  const handleConfirm = () => {
    const confirmation = buildConfirmation()
    confirmMutation.mutate(confirmation)
  }

  return (
    <main className="max-w-4xl mx-auto space-y-5 p-4">
      <header className="flex items-center gap-3">
        <Link className="btn btn-ghost gap-1" to="/matches">
          <ChevronLeft size={16} /> Partidos
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Revisar planilla</h1>
          <p className="text-sm text-gray-500">
            {fixture.home_registration.display_name} vs {fixture.away_registration.display_name}
            · {fixture.scheduled_date ?? 'Sin fecha'} · {fixture.stage.name}
          </p>
        </div>
      </header>

      <section className="card space-y-4">
        <h2 className="text-lg font-semibold">Compatibilidad de equipos</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <p className="font-medium text-gray-700">Local (planilla)</p>
            <p className="text-sm text-gray-500">{preview.home_team.name}</p>
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${homeBadge.className}`}
              >
                {homeBadge.label}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Esperado: {home_compatibility.expected_name} ({home_compatibility.expected_variant ?? '—'})
            </p>
            <p className="text-xs text-gray-500">
              Parseado: {home_compatibility.parsed_name ?? '—'} ({home_compatibility.parsed_variant ?? '—'})
            </p>
          </div>
          <div className="space-y-2">
            <p className="font-medium text-gray-700">Visitante (planilla)</p>
            <p className="text-sm text-gray-500">{preview.away_team.name}</p>
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${awayBadge.className}`}
              >
                {awayBadge.label}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Esperado: {away_compatibility.expected_name} ({away_compatibility.expected_variant ?? '—'})
            </p>
            <p className="text-xs text-gray-500">
              Parseado: {away_compatibility.parsed_name ?? '—'} ({away_compatibility.parsed_variant ?? '—'})
            </p>
          </div>
        </div>
      </section>

      <section className="card space-y-4">
        <h2 className="text-lg font-semibold">Reconciliación de marcador</h2>
        <div className="flex items-center gap-4">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${scoreBadge.className}`}
          >
            {scoreBadge.label}
          </span>
          <div className="text-sm text-gray-600">
            Planilla: {preview.home_team.players.reduce((sum, p) => sum + p.goals, 0)} -{' '}
            {preview.away_team.players.reduce((sum, p) => sum + p.goals, 0)}
            {' '}·{' '}
            Fixture: {fixture.source_home_score ?? '?'} - {fixture.source_away_score ?? '?'}
          </div>
        </div>
      </section>

      <section className="card space-y-4">
        <h2 className="text-lg font-semibold">Jugadores parseados</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="font-medium mb-2">Local</p>
            <ul className="space-y-1 text-sm">
              {preview.home_team.players.map((player) => (
                <li key={player.number} className="flex justify-between">
                  <span>#{player.number} {player.name}</span>
                  <span className="text-gray-500">
                    G:{player.goals} A:{player.yellow} 2':{player.two_min} R:{player.red}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-medium mb-2">Visitante</p>
            <ul className="space-y-1 text-sm">
              {preview.away_team.players.map((player) => (
                <li key={player.number} className="flex justify-between">
                  <span>#{player.number} {player.name}</span>
                  <span className="text-gray-500">
                    G:{player.goals} A:{player.yellow} 2':{player.two_min} R:{player.red}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="text-xs text-gray-500">
          Las identidades de jugadores se resolverán en el siguiente paso (página de plantel).
        </p>
      </section>

      <div className="flex gap-3 justify-end">
        <Link className="btn btn-ghost" to="/matches">
          Cancelar
        </Link>
        <button
          className="btn btn-primary"
          disabled={!isCompatible || confirmMutation.isPending}
          onClick={handleConfirm}
        >
          {confirmMutation.isPending ? 'Confirmando…' : 'Confirmar planilla'}
        </button>
      </div>

      {confirmMutation.isError && (
        <p className="text-sm text-red-600 text-center">
          No se pudo confirmar. Revisá la compatibilidad de equipos.
        </p>
      )}
    </main>
  )
}
