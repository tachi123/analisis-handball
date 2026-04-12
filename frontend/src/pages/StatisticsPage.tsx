import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts'
import { getMatch, getEvents } from '../api/client'
import type { Event } from '../types'

const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2']

// ── Player stats ──────────────────────────────────────────────────────────────

interface PlayerRow {
  name: string
  goals: number
  shots: number
  assists: number
  losses: number
  fouls: number
  sanctions: number
}

function buildPlayerStats(events: Event[]): PlayerRow[] {
  const map = new Map<number, PlayerRow>()
  for (const ev of events) {
    if (!ev.player_id || !ev.player) continue
    const pid = ev.player_id
    if (!map.has(pid))
      map.set(pid, { name: ev.player.name, goals: 0, shots: 0, assists: 0, losses: 0, fouls: 0, sanctions: 0 })
    const s = map.get(pid)!
    if (ev.action_type === 'Lanzamiento' || ev.action_type === '7 Metros') {
      s.shots++
      if (ev.result === 'Gol' || ev.result === 'Gol (Arco Vacío)') s.goals++
    }
    if (ev.action_type === 'Pérdida') s.losses++
    if (ev.action_type === 'Falta') s.fouls++
    if (ev.sanction_type) s.sanctions++
  }
  // Count assists (via assist_player_id on goal events)
  for (const ev of events) {
    if (!ev.assist_player_id) continue
    if (ev.result !== 'Gol' && ev.result !== 'Gol (Arco Vacío)') continue
    const pid = ev.assist_player_id
    if (!map.has(pid) && ev.assist_player)
      map.set(pid, { name: ev.assist_player.name, goals: 0, shots: 0, assists: 0, losses: 0, fouls: 0, sanctions: 0 })
    const s = map.get(pid)
    if (s) s.assists++
  }
  return Array.from(map.values()).sort((a, b) => b.goals - a.goals || b.assists - a.assists)
}

// ── Goalkeeper stats ─────────────────────────────────────────────────────────

interface GoalkeeperRow {
  name: string
  saves: number
  goalsReceived: number
  total: number
  savePercent: number
  byZone: Record<string, { saves: number; goals: number }>
}

function buildGoalkeeperStats(events: Event[]): GoalkeeperRow[] {
  // Shots where goalkeeper_id is present
  const map = new Map<number, GoalkeeperRow>()
  for (const ev of events) {
    if (!ev.goalkeeper_id) continue
    if (ev.action_type !== 'Lanzamiento' && ev.action_type !== '7 Metros') continue
    const gid = ev.goalkeeper_id
    if (!map.has(gid)) {
      const gkName = ev.goalkeeper?.name ?? `GK#${gid}`
      map.set(gid, { name: gkName, saves: 0, goalsReceived: 0, total: 0, savePercent: 0, byZone: {} })
    }
    const s = map.get(gid)!
    s.total++
    const isGoal = ev.result === 'Gol' || ev.result === 'Gol (Arco Vacío)'
    if (ev.result === 'Atajada') s.saves++
    if (isGoal) s.goalsReceived++

    // Zone breakdown
    const zone = ev.shot_zone ?? 'Sin zona'
    if (!s.byZone[zone]) s.byZone[zone] = { saves: 0, goals: 0 }
    if (ev.result === 'Atajada') s.byZone[zone].saves++
    if (isGoal) s.byZone[zone].goals++
  }
  for (const s of map.values()) {
    const relevant = s.saves + s.goalsReceived
    s.savePercent = relevant > 0 ? Math.round((s.saves / relevant) * 100) : 0
  }
  return Array.from(map.values()).sort((a, b) => b.total - a.total)
}

// ── Score timeline ───────────────────────────────────────────────────────────

function buildTimeline(events: Event[], homeName: string) {
  let home = 0, away = 0
  const data = [{ minute: 0, home: 0, away: 0 }]
  for (const ev of events) {
    if (ev.result !== 'Gol' && ev.result !== 'Gol (Arco Vacío)') continue
    const min = Math.floor(ev.game_timestamp / 60)
    if (ev.team_action === homeName) home++
    else away++
    data.push({ minute: min, home, away })
  }
  return data
}

// ── Attack phase efficiency ──────────────────────────────────────────────────

function buildPhaseStats(events: Event[]) {
  const map = new Map<string, { shots: number; goals: number }>()
  for (const ev of events) {
    if (!ev.attack_phase) continue
    if (ev.action_type !== 'Lanzamiento' && ev.action_type !== '7 Metros') continue
    if (!map.has(ev.attack_phase)) map.set(ev.attack_phase, { shots: 0, goals: 0 })
    const s = map.get(ev.attack_phase)!
    s.shots++
    if (ev.result === 'Gol' || ev.result === 'Gol (Arco Vacío)') s.goals++
  }
  return Array.from(map.entries()).map(([phase, s]) => ({
    phase,
    shots: s.shots,
    goals: s.goals,
    pct: s.shots > 0 ? Math.round((s.goals / s.shots) * 100) : 0,
  }))
}

// ── Tab types ────────────────────────────────────────────────────────────────

type TeamFilter = 'all' | 'home' | 'away'
type StatsTab = 'general' | 'portero' | 'fases'

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default function StatisticsPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const id = Number(matchId)
  const navigate = useNavigate()
  const [teamFilter, setTeamFilter] = useState<TeamFilter>('all')
  const [tab, setTab] = useState<StatsTab>('general')

  const { data: match } = useQuery({ queryKey: ['match', id], queryFn: () => getMatch(id) })
  const { data: allEvents = [], isLoading } = useQuery({ queryKey: ['events', id], queryFn: () => getEvents(id) })

  const homeName = match?.home_team?.name ?? ''
  const awayName = match?.away_team?.name ?? ''

  const events = allEvents.filter(e => {
    if (teamFilter === 'home') return e.team_action === homeName
    if (teamFilter === 'away') return e.team_action === awayName
    return true
  })

  // Derived data
  const playerStats = buildPlayerStats(events)
  const goalkeeperStats = buildGoalkeeperStats(allEvents) // GK stats always from all events
  const timelineData = buildTimeline(allEvents, homeName)
  const phaseStats = buildPhaseStats(events)

  const shots = events.filter(e => e.action_type === 'Lanzamiento' || e.action_type === '7 Metros')
  const goals = shots.filter(e => e.result === 'Gol' || e.result === 'Gol (Arco Vacío)').length
  const efficacy = shots.length > 0 ? Math.round((goals / shots.length) * 100) : 0
  const losses = events.filter(e => e.action_type === 'Pérdida').length
  const sanctions = events.filter(e => !!e.sanction_type).length

  const shotResults = shots.reduce<Record<string, number>>((acc, e) => {
    const k = e.result ?? 'Sin resultado'
    acc[k] = (acc[k] ?? 0) + 1
    return acc
  }, {})

  const shotZones = events
    .filter(e => e.shot_zone)
    .reduce<Record<string, number>>((acc, e) => {
      acc[e.shot_zone!] = (acc[e.shot_zone!] ?? 0) + 1
      return acc
    }, {})

  const TEAM_TABS: { key: TeamFilter; label: string }[] = [
    { key: 'all', label: 'Ambos' },
    { key: 'home', label: homeName || 'Local' },
    { key: 'away', label: awayName || 'Visitante' },
  ]

  const STAT_TABS: { key: StatsTab; label: string }[] = [
    { key: 'general', label: 'General' },
    { key: 'portero', label: 'Portero' },
    { key: 'fases', label: 'Fases' },
  ]

  if (isLoading) return <div className="p-4 text-gray-400">Cargando estadísticas…</div>

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(`/match/${id}/live`)} className="text-gray-400 hover:text-gray-700 p-1">
          <ChevronLeft size={24} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-gray-900 truncate">
            {homeName || '?'} vs {awayName || '?'}
          </h1>
          <p className="text-sm text-gray-500">{allEvents.length} eventos · {match?.date}</p>
        </div>
      </div>

      {/* Team filter tabs */}
      <div className="flex rounded-xl overflow-hidden border border-gray-200 bg-gray-100 p-1 gap-1">
        {TEAM_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTeamFilter(t.key)}
            className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors truncate px-2 ${
              teamFilter === t.key ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* View tabs */}
      <div className="flex gap-1">
        {STAT_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all ${
              tab === t.key ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── GENERAL TAB ──────────────────────────────────────────────────── */}
      {tab === 'general' && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-5 gap-2">
            {[
              { label: 'Goles', value: goals, color: 'text-green-700' },
              { label: 'Lanz.', value: shots.length, color: 'text-blue-700' },
              { label: 'Eficacia', value: `${efficacy}%`, color: efficacy >= 50 ? 'text-green-700' : 'text-orange-600' },
              { label: 'Pérd.', value: losses, color: 'text-red-600' },
              { label: 'Sanc.', value: sanctions, color: 'text-orange-600' },
            ].map(s => (
              <div key={s.label} className="card text-center py-3">
                <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Score timeline */}
          {timelineData.length > 1 && (
            <div className="card">
              <h2 className="font-semibold mb-3">Evolución del marcador</h2>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="minute" tick={{ fontSize: 11 }} label={{ value: 'Min', position: 'insideBottomRight', offset: -5, fontSize: 10 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip formatter={(v: number, name: string) => [v, name === 'home' ? homeName : awayName]} />
                  <Legend formatter={(v: string) => v === 'home' ? homeName : awayName} />
                  <Line type="stepAfter" dataKey="home" stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line type="stepAfter" dataKey="away" stroke="#dc2626" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Pie + Bar side by side on larger screens */}
          <div className="grid md:grid-cols-2 gap-4">
            {Object.keys(shotResults).length > 0 && (
              <div className="card">
                <h2 className="font-semibold mb-3 text-sm">Resultado de lanzamientos</h2>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie data={Object.entries(shotResults).map(([name, value]) => ({ name, value }))} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70}>
                      {Object.keys(shotResults).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {Object.keys(shotZones).length > 0 && (
              <div className="card">
                <h2 className="font-semibold mb-3 text-sm">Lanzamientos por zona</h2>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={Object.entries(shotZones).map(([name, value]) => ({ name, value }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Player table */}
          {playerStats.length > 0 && (
            <div className="card overflow-x-auto">
              <h2 className="font-semibold mb-3">Por jugador</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 text-xs border-b">
                    <th className="pb-2">Jugador</th>
                    <th className="pb-2 text-center">G</th>
                    <th className="pb-2 text-center">L</th>
                    <th className="pb-2 text-center">%</th>
                    <th className="pb-2 text-center">A</th>
                    <th className="pb-2 text-center">P</th>
                    <th className="pb-2 text-center">S</th>
                  </tr>
                </thead>
                <tbody>
                  {playerStats.map(p => (
                    <tr key={p.name} className="border-b border-gray-50 last:border-0">
                      <td className="py-2 font-medium">{p.name}</td>
                      <td className="text-center font-bold text-green-700">{p.goals}</td>
                      <td className="text-center">{p.shots}</td>
                      <td className="text-center text-gray-500">{p.shots > 0 ? Math.round((p.goals / p.shots) * 100) : 0}%</td>
                      <td className="text-center text-indigo-600 font-semibold">{p.assists || ''}</td>
                      <td className="text-center text-red-600">{p.losses}</td>
                      <td className="text-center text-orange-600">{p.sanctions || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-[10px] text-gray-400 mt-2">G = Goles · L = Lanzamientos · A = Asistencias · P = Pérdidas · S = Sanciones</p>
            </div>
          )}
        </>
      )}

      {/* ── PORTERO TAB ──────────────────────────────────────────────────── */}
      {tab === 'portero' && (
        <>
          {goalkeeperStats.length === 0 ? (
            <div className="card text-center py-8 text-gray-400">
              <p className="text-lg font-semibold">Sin datos de portero</p>
              <p className="text-sm mt-1">Los datos de atajadas se registran automáticamente cuando hay un portero en el plantel</p>
            </div>
          ) : (
            goalkeeperStats.map(gk => (
              <div key={gk.name} className="space-y-4">
                {/* GK header */}
                <div className="card">
                  <h2 className="font-bold text-lg mb-3">{gk.name}</h2>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div>
                      <p className="text-2xl font-black text-green-700">{gk.savePercent}%</p>
                      <p className="text-[10px] text-gray-500">Save %</p>
                    </div>
                    <div>
                      <p className="text-2xl font-black text-blue-700">{gk.saves}</p>
                      <p className="text-[10px] text-gray-500">Atajadas</p>
                    </div>
                    <div>
                      <p className="text-2xl font-black text-red-600">{gk.goalsReceived}</p>
                      <p className="text-[10px] text-gray-500">Goles Rec.</p>
                    </div>
                    <div>
                      <p className="text-2xl font-black text-gray-700">{gk.total}</p>
                      <p className="text-[10px] text-gray-500">Total Lanz.</p>
                    </div>
                  </div>
                </div>

                {/* GK zone breakdown */}
                {Object.keys(gk.byZone).length > 0 && (
                  <div className="card">
                    <h3 className="font-semibold mb-3 text-sm">Rendimiento por zona</h3>
                    <div className="space-y-2">
                      {Object.entries(gk.byZone).map(([zone, { saves, goals }]) => {
                        const total = saves + goals
                        const pct = total > 0 ? Math.round((saves / total) * 100) : 0
                        return (
                          <div key={zone} className="flex items-center gap-3">
                            <span className="text-sm font-medium w-20">{zone}</span>
                            <div className="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden relative">
                              <div
                                className="h-full bg-green-500 rounded-full transition-all"
                                style={{ width: `${pct}%` }}
                              />
                              <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold">
                                {saves}/{total} ({pct}%)
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </>
      )}

      {/* ── FASES TAB ────────────────────────────────────────────────────── */}
      {tab === 'fases' && (
        <>
          {phaseStats.length === 0 ? (
            <div className="card text-center py-8 text-gray-400">
              <p className="text-lg font-semibold">Sin datos de fases de ataque</p>
              <p className="text-sm mt-1">Seleccioná la fase de ataque durante el etiquetado para ver esta información</p>
            </div>
          ) : (
            <>
              {/* Phase efficiency cards */}
              <div className="grid grid-cols-2 gap-3">
                {phaseStats.map(p => (
                  <div key={p.phase} className="card text-center py-4">
                    <p className="text-xs font-bold text-gray-500 uppercase mb-1">{p.phase}</p>
                    <p className={`text-3xl font-black ${p.pct >= 50 ? 'text-green-700' : 'text-orange-600'}`}>
                      {p.pct}%
                    </p>
                    <p className="text-xs text-gray-400 mt-1">{p.goals}/{p.shots} goles</p>
                  </div>
                ))}
              </div>

              {/* Phase bar chart */}
              <div className="card">
                <h2 className="font-semibold mb-3 text-sm">Comparativa por fase</h2>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={phaseStats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="phase" tick={{ fontSize: 10 }} />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="goals" name="Goles" fill="#16a34a" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="shots" name="Lanz." fill="#93c5fd" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
