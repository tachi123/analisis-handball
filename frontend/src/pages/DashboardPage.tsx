import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'

/**
 * Dashboard de mano statica para Match 99.
 * Lee reports/public/report.json y muestra:
 *  - Selector de partido superior con marcador y cobertura
 *  - Comparación de equipos tarjetas/gráficos
 *  - Jugadores de campo con filtros y tarjetas
 *  - Arqueros sección visual
 *  - Línea de tiempo de incidentes con paginación "mostrar 6 más"
 *  - Enlaces de video cuando estén aprobados públicamente
 */

type PlayerCard = {
  slug: string
  name: string
  jersey_number: number | null
  team_side: 'home' | 'away' | 'unknown'
  role: 'field_player' | 'goalkeeper'
  metrics: Record<string, unknown>
}

type Incident = {
  reference: string
  period: number | null
  regulation_seconds: number | null
  clock_unverified: boolean
  clock_label: string | null
  incident_type: string
  outcome: string | null
  team_side: 'home' | 'away' | 'unknown'
  player_name: string | null
  player_slug: string | null
  event_kind: string | null
}

type MatchData = {
  schema_version: string
  report_version: number
  match: {
    date: string
    home_team: string
    away_team: string
  }
  source: { label: string; status: string }
  coaching: {
    question: string
    pattern_statement: string
    action: { kind: string; text: string }
  }
  metrics: Record<string, { count?: number; numerator?: number; denominator?: unknown; excluded?: number; unknown?: number; clock_unverified?: number }>
  reconciliation: Array<{ side: string; official: number; analytical: number; discrepancy: number }>
  uncertainty_disclosure: string
  players: PlayerCard[]
  evidence: Array<{ reference: string; period?: number; regulation_seconds?: number; clock_unverified?: boolean; observation: string; media_available?: boolean; media_url?: string }>
  coverage: { analyzed_periods: number[]; status: string; label: string | null } | null
  team_summary: {
    home: { name: string; side: string; shots: number; goals: number; turnovers: number; recoveries: number; sanctions: number }
    away: { name: string; side: string; shots: number; goals: number; turnovers: number; recoveries: number; sanctions: number }
  }
  incidents: Incident[]
}

/** Formatea un número como jerseys humanos */
function formatJersey(num: number | null | undefined): string {
  if (num === null || num === undefined) return '—'
  return String(num)
}

/** Etiqueta de tiempo del reloj — no inventa tiempos, muestra etiqueta explícita */
function clockLabel(regulation_seconds: number | null, clock_unverified: boolean): string {
  if (regulation_seconds !== null && !clock_unverified) {
    const mins = Math.floor(regulation_seconds / 60)
    const secs = regulation_seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  if (clock_unverified) {
    return 'Reloj sin verificar'
  }
  return 'Sin tiempo disponible'
}

/** Mapea el tipo de evento canónico a descripción en español */
function incidentType(kind: string | null): string {
  const map: Record<string, string> = {
    shot: 'Lanzamiento',
    turnover: 'Pérdida',
    recovery: 'Recuperación',
    foul_sanction: 'Sanción',
    other: 'Incidencia de juego',
  }
  return map[kind] || 'Incidencia'
}

/** Determina el lado del equipo (home/away/unknown) */
function teamSide(team_id: number | null, home_id: number, away_id: number): 'home' | 'away' | 'unknown' {
  if (team_id === home_id) return 'home'
  if (team_id === away_id) return 'away'
  return 'unknown'
}

/** Renderiza un pequeño gráfico de barras horizontal con CSS (sin chart library) */
function ShotEfficiencyBar({ made, attempts }: { made: number; attempts: number }, maxWidth: number = 100) {
  if (!attempts || attempts === 0) return null
  const pct = made / attempts
  const width = Math.round(pct * maxWidth)
  return (
    <div className="flex items-baseline gap-1 text-xs">
      <span className="w-max text-gray-600">{made}</span>
      <div className="flex-1 h-1.5 bg-gray-200 rounded overflow-hidden">
        <div
          className={`h-full bg-green-600 rounded overflow-hidden transition-all duration-200`}
          style={{ width: `${Math.max(0, Math.min(maxWidth, width))}%` }}
        />
      </div>
      <span className="w-max text-gray-500 text-opacity-40">of {attempts}</span>
    </div>
  )
}

/** Componente de selector de partido superior */
function MatchSelector({ match }: { match: MatchData['match'] }) {
  const navigate = useNavigate()
  return (
    <div className="border-b border-gray-200 bg-white p-3 mb-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-medium text-lg text-gray-900">
            {match.home_team} vs {match.away_team}
          </span>
        </div>
        <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover underline">
          ← Cambiar
        </button>
      </div>
      <div className="mt-2 flex flex-col sm:flex-row gap-2">
        <span className="text-sm text-gray-500">
          {match.date}
        </span>
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">
            {data.coverage?.status === 'complete' ? 'Completa' : data.coverage?.status === 'partial' ? 'Parcial' : 'Sin cobertura'}
          </span>
        </div>
      </div>
    </div>
  )
}

/** Componente de comparación de equipos */
function TeamComparison({ team_summary }: { team_summary: MatchData['team_summary']; home_team: string; away_team: string }) {
  const home = team_summary.home
  const away = team_summary.away

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
      <div className="card border-indigo-200 p-4">
        <h2 className="font-semibold text-indigo-800 mb-3">S.A.P.A.</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <p className="font-medium">Goles</p>
            <p className="font-black text-2xl text-green-600">{home.goals}</p>
          </div>
          <div>
            <p className="font-medium">Lanzamientos</p>
            <p className="font-black text-2xl text-blue-600">{home.shots}</p>
          </div>
          <div>
            <p className="font-medium">Efectividad</p>
            <p className="text-sm text-indigo-600">
              {home.shots > 0 ? `${Math.round((home.goals / home.shots) * 100)}%` : '—'}
            </p>
          </div>
          <div>
            <p className="font-medium">Pérdidas</p>
            <p className="text-red-600">{home.turnovers}</p>
          </div>
          <div>
            <p className="font-medium">Recuperaciones</p>
            <p className="text-orange-600">{home.recoveries}</p>
          </div>
          <div>
            <p className="font-medium">Sanciones</p>
            <p className="text-orange-600">{home.sanctions}</p>
          </div>
        </div>
      </div>

      <div className="card border-indigo-200 p-4">
        <h2 className="font-semibold text-indigo-800 mb-3">Palermo Handball</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <p className="font-medium">Goles</p>
            <p className="font-black text-2xl text-green-600">{away.goals}</p>
          </div>
          <div>
            <p className="font-medium">Lanzamientos</p>
            <p className="font-black text-2xl text-blue-600">{away.shots}</p>
          </div>
          <div>
            <p className="font-medium">Efectividad</p>
            <p className="text-sm text-indigo-600">
              {away.shots > 0 ? `${Math.round((away.goals / away.shots) * 100)}%` : '—'}
            </p>
          </div>
          <div>
            <p className="font-medium">Pérdidas</p>
            <p className="text-red-600">{away.turnovers}</p>
          </div>
          <div>
            <p className="font-medium">Recuperaciones</p>
            <p className="text-orange-600">{away.recoveries}</p>
          </div>
          <div>
            <p className="font-medium">Sanciones</p>
            <p className="text-orange-600">{away.sanctions}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Tarjeta de jugador de campo */
function FieldPlayerCard({ player }: { player: PlayerCard }) {
  const metrics = player.metrics
  const shots = metrics.shots ?? 0
  const goals = metrics.goals ?? 0
  const conversion = shots > 0 ? Math.round((goals / shots) * 100) : null
  const turnovers = metrics.turnovers ?? 0
  const recoveries = metrics.recoveries ?? 0
  const sanctions = metrics.sanctions ?? 0

  return (
    <div key={player.slug} className="card border-gray-200 p-3 hover:border-indigo-300 transition-colors">
      <div className="flex items-center gap-2">
        <span className="font-medium text-gray-900">{player.name}</span>
        <span className="text-xs text-gray-400">#{formatJersey(player.jersey_number)}</span>
      </div>
      <div className="grid grid-cols-2 gap-1 mt-2 text-xs">
        <div>
          <span className="font-medium text-indigo-600">S</span>
          <span>{shots}</span>
        </div>
        <div>
          <span className="font-medium text-green-600">G</span>
          <span>{goals}</span>
        </div>
        <div>
          <span className="font-medium text-indigo-600">%</span>
          {conversion !== null ? (
            <span>{conversion}%</span>
          ) : (
            <span className="text-gray-500">—</span>
          )}
        </div>
        <div>
          <span className="font-medium text-red-600">P</span>
          <span>{turnovers}</span>
        </div>
        <div>
          <span className="font-medium text-orange-600">R</span>
          <span>{recoveries}</span>
        </div>
        <div>
          <span className="font-medium text-orange-600">S</span>
          <span>{sanctions}</span>
        </div>
      </div>
    </div>
  )
}

/** Componente de arquera */
function GoalkeeperCard({ player }: { player: PlayerCard }) {
  const metrics = player.metrics
  const saves = metrics.saves ?? 0
  const shots_faced = metrics.shots_faced ?? 0
  const goals_conceded = metrics.goals_conceded ?? 0
  const save_rate = shots_faced > 0 ? Math.round((saves / shots_faced) * 100) : 0

  return (
    <div key={player.slug} className="card border-red-200 p-4">
      <h2 className="font-bold text-red-700 mb-3">{player.name}</h2>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="font-black text-3xl text-red-600">{save_rate}%</p>
          <p className="text-xs text-gray-500">Save %</p>
        </div>
        <div>
          <p className="font-black text-3xl text-blue-600">{saves}</p>
          <p className="text-xs text-gray-500">Atajadas</p>
        </div>
        <div>
          <p className="font-black text-3xl text-red-400">{goals_conceded}</p>
          <p className="text-xs text-gray-500">Goles</p>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-red-200">
        <p className="text-xs text-gray-500">Shots faced: {shots_faced}</p>
      </div>
    </div>
  )
}

/** Línea de tiempo de incidentes con paginación "mostrar 6 más" */
function IncidentsTimeline({ incidents, onFilterChange }: { incidents: Incident[]; onFilterChange?: (filters: { team?: string; player?: string; incident_type?: string }) => void }) {
  const [visible, setVisible] = useState(6)
  const [filters, setFilters] = useState({ team: '', player: '', incident_type: '' })

  // Filtrar incidentes aplicados
  const filtered = incidents.filter(inc => {
    if (filters.team && inc.team_side !== filters.team) return false
    if (filters.player && (inc.player_name !== filters.player && inc.player_name !== null)) return false
    if (filters.incident_type && inc.incident_type !== filters.incident_type) return false
    return true
  })

  // Efecto: al cambiar filtros, reiniciar a 6 visibles
  useEffect(() => {
    setVisible(6)
  }, [filters])

  const visibleIncidents = filtered.slice(0, visible)
  const hasMore = filtered.length > visible

  const handleShowMore = () => {
    setVisible(prev => Math.min(prev + 6, filtered.length))
  }

  const applyFilters = (newFilters: { team?: string; player?: string; incident_type?: string }) => {
    setFilters(newFilters)
  }

  // Opciones de filtro
  const teamOptions = [
    { value: 'all', label: 'Todos' },
    { value: 'home', label: 'S.A.P.A.' },
    { value: 'away', label: 'Palermo Handball' },
  ]

  const incidentTypeOptions = [
    { value: 'all', label: 'Todos' },
    { value: 'Lanzamiento', label: 'Lanzamiento' },
    { value: 'Pérdida', label: 'Pérdida' },
    { value: 'Recuperación', label: 'Recuperación' },
    { value: 'Sanción', label: 'Sanción' },
    { value: 'Incidencia de juego', label: 'Incidencia de juego' },
  ]

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-semibold mb-3">Línea de tiempo de incidentes</h2>
        <p className="text-sm text-gray-500">
          {filtered.length} incidentes totales · {visible} mostrados
        </p>

        {/* Filtros */}
        {filtered.length > 0 && (
          <div className="grid grid-cols-2 gap-2 mb-3">
            <select
              value={filters.team}
              onChange={(e) => applyFilters({ team: e.target.value })} className="rounded border p-1 text-sm"
            >
              {teamOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <select
              value={filters.player}
              onChange={(e) => applyFilters({ player: e.target.value })} className="rounded border p-1 text-sm"
            >
              {playerOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <select
              value={filters.incident_type}
              onChange={(e) => applyFilters({ incident_type: e.target.value })} className="rounded border p-1 text-sm"
            >
              {incidentTypeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        )}

        {/* Lista de incidentes visibles */}
        <div className="space-y-2">
          {visibleIncidents.map((inc, i) => (
            <div key={i} className="card border-gray-200 p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-indigo-600">{inc.incident_type}</span>
                  <span className="text-xs text-gray-500">{inc.period ? `P${inc.period}` : '—'}</span>
                </div>
                <span className="text-sm font-medium {inc.team_side === 'home' ? 'text-indigo-600' : inc.team_side === 'away' ? 'text-red-600' : 'text-gray-500'}">
                  {inc.team_side}
                </span>
              </div>
              <p className="text-sm font-medium">
                {inc.outcome || '—'}
              </p>
              {inc.player_name && (
                <p className="text-xs text-gray-500">Jugador: {inc.player_name}</p>
              )}
              <p className="text-xs text-gray-500">{inc.clock_label || 'Sin tiempo disponible'}</p>
            </div>
          ))}

          {filtered.length > visible && (
            <button onClick={handleShowMore} className="mt-2 w-full text-left text-indigo-600 hover underline text-sm">
              Mostrar 6 más
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/** Componente de disponibilidad de video */
function VideoSection({ evidence }: { evidence: Array<{ media_available?: boolean; media_url?: string }> }) {
  const hasPublicVideo = evidence.some(
    item => item.media_available && item.media_url && item.media_url.startsWith('https://www.youtube.com/watch')
  )
  if (!hasPublicVideo) {
    return (
      <div className="card border-yellow-200 p-4 mb-6">
        <h2 className="font-semibold text-yellow-800 mb-3">Enlace de video</h2>
        <p className="text-sm text-yellow-600">
          Las vinculaciones de video no están disponibles para esta publicación.
        </p>
      </div>
    )
  }
  return (
    <div className="card border-yellow-200 p-4 mb-6">
      <h2 className="font-semibold text-yellow-800 mb-3">Enlace de video</h2>
      <p className="text-sm text-yellow-600">
        Los enlaces de video están disponibles para esta publicación.
      </p>
    </div>
  )
}
export default function DashboardPage() {
  const [data, setData] = useState<MatchData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    async function loadReport() {
      try {
        // Intentar fetch from /reports/public/report.json (servido por Vite static server)
        const resp = await fetch('/report.json', { cache: 'no-cache' })
        if (!resp.ok) throw new Error('No se pudo cargar el reporte')
        const result = await resp.json()
        setData(result)
        setError(null)
      } catch (e: any) {
        setError(e.message || 'Error inesperado cargando el reporte')
        setData(null)
      }
    }
    loadReport()
  }, [])

  if (!data) {
    return (
      <div className="p-8 text-center text-gray-500">
        <h1 className="text-2xl font-bold mb-4">Dashboard de mano statica</h1>
        <p>{error || 'Cargando reporte…</p>
        <p className="text-sm">Coloca report_match99.json en reports/public/report.json</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <MatchSelector match={data.match} />

      <TeamComparison team_summary={data.team_summary} home_team={data.match.home_team} away_team={data.match.away_team} />

      {/* Disponibilidad de video */}
      <VideoSection evidence={data.evidence} />

      {/* Field players section */}
      <div className="grid grid-cols-1 gap-4 mb-6">
        <div className="card border-green-200 p-4">
          <h2 className="font-semibold text-green-800 mb-3">Jugadores de campo</h2>
          <p className="text-sm text-gray-500">Filtrar por equipo:</p>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <button className="rounded border p-1 text-xs text-green-600 hover:bg-green-100">Todos</button>
            <button className="rounded border p-1 text-xs text-indigo-600 hover:bg-indigo-100">S.A.P.A.</button>
            <button className="rounded border p-1 text-xs text-red-600 hover:bg-red-100">Palermo</button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {data.players
              .filter((p) => p.role === 'field_player')
              .sort((a, b) => (a.metrics.shots ?? 0) - (b.metrics.shots ?? 0))
              .map((player) => (
                <FieldPlayerCard key={player.slug} player={player} />
              ))}
          </div>
        </div>

        <div className="card border-red-200 p-4">
          <h2 className="font-semibold text-red-800 mb-3">Arqueros</h2>
          <p className="text-sm text-gray-500">Arqueros registrados:</p>
          <div className="grid grid-cols-2 gap-3">
            {data.players
              .filter((p) => p.role === 'goalkeeper')
              .map((player) => <GoalkeeperCard key={player.slug} player={player} />}
            )}
          </div>
        </div>
      </div>

      {/* Incidents timeline */}
      <IncidentsTimeline incidents={data.incidents} onFilterChange={undefined} />
    </div>
  )
}