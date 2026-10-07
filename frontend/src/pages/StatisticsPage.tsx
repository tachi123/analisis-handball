import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { ChevronLeft } from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts'
import { approveReportPackage, attestRecoveryArtifact, createReportPackage, getCanonicalMetrics, getCanonicalReconciliation, getEvents, getMatch, getPublicationStatus, getReviewedMetrics, getWarningsSummary, publishReportPackage } from '../api/client'
import WarningsPanel from '../components/WarningsPanel'
import PdfReportExport from '../components/PdfReportExport'
import type { Event, ReportPackageActionKind, ReportPackageEvidenceInput, ReportPublicationStatus, ReviewedMetric, ReviewedReportPackage } from '../types'

const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2']

const METRIC_LABELS: Record<string, string> = {
  shot_conversion: 'Conversión de lanzamientos',
  seven_meter_conversion: 'Conversión de 7 metros',
  observed_goalkeeper_save_rate: 'Atajadas por decisión observada',
  confirmed_assist: 'Asistencias confirmadas',
  recovery: 'Recuperaciones',
  defensive_action: 'Acciones defensivas visibles',
  foul_sanction: 'Faltas o sanciones',
  transition_outcome: 'Resultados de transición',
  goalkeeper_outcome: 'Resultados de arquero',
}

function metricLabel(key: string) {
  if (key.startsWith('turnover:')) return `Pérdidas: ${key.slice('turnover:'.length).replace(/_/g, ' ')}`
  return METRIC_LABELS[key] ?? key
}

function MetricContext({ metric }: { metric: ReviewedMetric }) {
  const denominator = metric.denominator
  const hasDenominator = typeof denominator === 'number'
  const rate = hasDenominator && denominator > 0
    ? `${Math.round((metric.numerator / denominator) * 100)}%`
    : null

  return <li className="rounded-lg border border-gray-100 p-3">
    <div className="flex items-baseline justify-between gap-3">
      <span className="font-medium text-gray-800">{metricLabel(metric.name)}</span>
      <span className="font-bold text-indigo-700">{rate ?? `${metric.count} conteo`}</span>
    </div>
    <p className="mt-1 text-xs text-gray-600">
      Conteo: {metric.count} · Numerador: {metric.numerator} · Denominador: {hasDenominator ? denominator : 'no aplicable'}
    </p>
    <p className="mt-1 text-xs text-gray-500">
      Excluidos: {metric.excluded} · Desconocidos: {metric.unknown} · Reloj no verificado: {metric.clock_unverified}
    </p>
  </li>
}

const ACTIONS: { value: ReportPackageActionKind; label: string }[] = [
  { value: 'keep', label: 'Mantener' }, { value: 'do', label: 'Hacer' }, { value: 'change', label: 'Cambiar' },
]

function validationMessage(error: unknown) {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail
  return error instanceof Error ? error.message : 'No se pudo validar el paquete.'
}

function emptyEvidence(): ReportPackageEvidenceInput {
  return { reference: '', period: 1, regulation_seconds: null, clock_unverified: false, public_observation: null, public_approved: false }
}

function PublicationControls({ packageRecord }: { packageRecord: ReviewedReportPackage }) {
  const queryClient = useQueryClient()
  const [dumpLocation, setDumpLocation] = useState('')
  const [pdfLocation, setPdfLocation] = useState('')
  const status = useQuery({ queryKey: ['publication-status', packageRecord.id], queryFn: () => getPublicationStatus(packageRecord.id), enabled: Boolean(packageRecord.approved_at) })
  const attest = useMutation({
    mutationFn: ({ artifactType, location }: { artifactType: 'postgres_dump' | 'imported_pdf_export'; location: string }) => attestRecoveryArtifact(packageRecord.id, artifactType, location),
    onSuccess: () => status.refetch(),
  })
  const publish = useMutation({
    mutationFn: () => publishReportPackage(packageRecord.id),
    onSuccess: (result) => queryClient.setQueryData<ReportPublicationStatus>(['publication-status', packageRecord.id], result),
  })
  const current = status.data
  const publishable = current?.status === 'ready' || current?.status === 'failed' || current?.status === 'published'
  const error = status.error ?? attest.error ?? publish.error

  return <section className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-3 space-y-3" aria-label="Publicación del informe">
    <div className="flex items-start justify-between gap-3"><div><h3 className="font-medium">Publicación del informe</h3><p className="text-xs text-gray-600">Las ubicaciones son declaraciones del operador; no se verifican archivos.</p></div><button type="button" className="text-sm text-indigo-700" onClick={() => status.refetch()}>Actualizar estado</button></div>
    {status.isLoading ? <p className="text-sm text-gray-500">Consultando preparación...</p> : current && <div role="status" className="text-sm"><p>Estado: {current.status}</p>{current.missing_recovery_artifacts.length > 0 && <p className="text-amber-700">Faltan: {current.missing_recovery_artifacts.join(', ')}</p>}{current.published_at && <p>Publicado: {new Date(current.published_at).toLocaleString()} · versión {current.report_version}</p>}</div>}
    <div className="grid gap-2 md:grid-cols-2"><label className="text-sm">Ubicación del dump PostgreSQL<input aria-label="Ubicación del dump PostgreSQL" className="mt-1 w-full rounded border p-2" value={dumpLocation} onChange={event => setDumpLocation(event.target.value)} /></label><label className="text-sm">Ubicación de la exportación PDF<input aria-label="Ubicación de la exportación PDF" className="mt-1 w-full rounded border p-2" value={pdfLocation} onChange={event => setPdfLocation(event.target.value)} /></label></div>
    <div className="flex flex-wrap gap-2"><button type="button" className="btn" disabled={!dumpLocation.trim() || attest.isPending} onClick={() => attest.mutate({ artifactType: 'postgres_dump', location: dumpLocation })}>Registrar dump</button><button type="button" className="btn" disabled={!pdfLocation.trim() || attest.isPending} onClick={() => attest.mutate({ artifactType: 'imported_pdf_export', location: pdfLocation })}>Registrar exportación PDF</button><button type="button" className="btn btn-primary" disabled={!publishable || publish.isPending} onClick={() => publish.mutate()}>{publish.isPending ? 'Publicando...' : current?.status === 'published' || current?.status === 'failed' ? 'Reintentar publicación' : 'Publicar'}</button></div>
    {error && <p role="alert" className="text-sm text-red-600">{validationMessage(error)}</p>}
    {current?.failure_message && <p role="alert" className="text-sm text-red-600">{current.failure_message}</p>}
    {current?.status === 'published' && current.public_url && <a className="text-sm font-medium text-indigo-700 underline" href={current.public_url} target="_blank" rel="noreferrer">Abrir informe público actual</a>}
  </section>
}

function PackageControls({ matchId, reviewedMetrics, canonicalEventIds = [] }: { matchId: number; reviewedMetrics: Record<string, ReviewedMetric> | undefined; canonicalEventIds?: number[] }) {
  const [question, setQuestion] = useState('')
  const [pattern, setPattern] = useState('')
  const [action, setAction] = useState<ReportPackageActionKind | null>(null)
  const [actionText, setActionText] = useState('')
  const [uncertainty, setUncertainty] = useState('')
  const [evidence, setEvidence] = useState<ReportPackageEvidenceInput[]>([emptyEvidence(), emptyEvidence(), emptyEvidence()])
  const [packageRecord, setPackageRecord] = useState<ReviewedReportPackage | null>(null)
  const selectedEvidence = evidence.filter(item => item.public_approved && item.reference.trim())
  const create = useMutation({
    mutationFn: (data: Parameters<typeof createReportPackage>[1]) => createReportPackage(matchId, data),
    onSuccess: setPackageRecord,
  })
  const approve = useMutation({ mutationFn: approveReportPackage, onSuccess: setPackageRecord })
  const submit = () => {
    if (!action || canonicalEventIds.length === 0) return
    create.mutate({ coaching_question: question, pattern_statement: pattern, action_kind: action, action_text: actionText, uncertainty_disclosure: uncertainty, metrics: reviewedMetrics ?? {}, reconciliation: [], source_label: null, source_status: 'canonical', canonical_event_ids: canonicalEventIds, evidence: selectedEvidence })
  }
  const updateEvidence = (index: number, patch: Partial<ReportPackageEvidenceInput>) => setEvidence(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item))
  const error = create.error ?? approve.error
  const approved = packageRecord?.approved_at !== null && packageRecord?.approved_at !== undefined

  return <section className="card space-y-3" aria-label="Paquete de revisión para coaching">
    <div><h2 className="font-semibold">Paquete de revisión</h2><p className="text-xs text-gray-500">Seleccioná únicamente evidencia aprobada para publicación. No se muestran notas privadas ni archivos multimedia.</p></div>
    {canonicalEventIds.length === 0 && <p role="alert" className="text-sm text-amber-700">No hay evidencia canónica elegible: se bloquean las afirmaciones tácticas.</p>}
    <label className="block text-sm">Pregunta de coaching<input className="mt-1 w-full rounded border p-2" value={question} onChange={event => setQuestion(event.target.value)} /></label>
    <label className="block text-sm">Patrón observado<textarea className="mt-1 w-full rounded border p-2" value={pattern} onChange={event => setPattern(event.target.value)} /></label>
    <fieldset><legend className="text-sm">Una acción</legend><div className="mt-1 flex gap-2">{ACTIONS.map(item => <label key={item.value} className="rounded border px-3 py-2 text-sm"><input type="radio" name="package-action" checked={action === item.value} onChange={() => setAction(item.value)} /> {item.label}</label>)}</div></fieldset>
    <label className="block text-sm">Acción concreta<input className="mt-1 w-full rounded border p-2" value={actionText} onChange={event => setActionText(event.target.value)} /></label>
    <label className="block text-sm">Incertidumbre o cobertura<textarea className="mt-1 w-full rounded border p-2" value={uncertainty} onChange={event => setUncertainty(event.target.value)} /></label>
    <div className="space-y-2"><h3 className="text-sm font-medium">Evidencia pública ({selectedEvidence.length}/3 mínimo, 8 máximo)</h3>{evidence.map((item, index) => <div key={index} className="grid gap-2 rounded border p-2 sm:grid-cols-[1fr_80px_auto]"><input aria-label={`Referencia de evidencia ${index + 1}`} className="rounded border p-2 text-sm" placeholder="Referencia observable" value={item.reference} onChange={event => updateEvidence(index, { reference: event.target.value })} /><input aria-label={`Período de evidencia ${index + 1}`} className="rounded border p-2 text-sm" type="number" min="1" value={item.period} onChange={event => updateEvidence(index, { period: Number(event.target.value) })} /><label className="text-sm"><input type="checkbox" checked={item.public_approved} onChange={event => updateEvidence(index, { public_approved: event.target.checked })} /> Pública aprobada</label></div>)}{evidence.length < 8 && <button type="button" className="text-sm text-indigo-700" onClick={() => setEvidence(current => [...current, emptyEvidence()])}>Agregar evidencia</button>}</div>
    {!action && <p className="text-sm text-amber-700">Elegí exactamente una acción: mantener, hacer o cambiar.</p>}
    {error && <p role="alert" className="text-sm text-red-600">{validationMessage(error)}</p>}
    {!packageRecord ? <button className="btn btn-primary" disabled={!action || canonicalEventIds.length === 0 || create.isPending} onClick={submit}>{create.isPending ? 'Guardando...' : 'Crear paquete para revisión'}</button> : <><div className="flex flex-wrap items-center gap-2"><span className="text-sm">Paquete v{packageRecord.report_version}: {approved ? 'aprobado y listo para publicación' : 'pendiente de aprobación'}</span>{!approved && <button className="btn btn-primary" disabled={approve.isPending} onClick={() => approve.mutate(packageRecord.id)}>{approve.isPending ? 'Validando...' : 'Aprobar paquete'}</button>}</div>{approved && <PublicationControls packageRecord={packageRecord} />}</>}
  </section>
}

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

export function LegacyStatisticsPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const id = Number(matchId)
  const navigate = useNavigate()
  const [teamFilter, setTeamFilter] = useState<TeamFilter>('all')
  const [tab, setTab] = useState<StatsTab>('general')

  const { data: match } = useQuery({ queryKey: ['match', id], queryFn: () => getMatch(id) })
  const { data: allEvents = [], isLoading } = useQuery({ queryKey: ['events', id], queryFn: () => getEvents(id) })
  const { data: reviewedMetrics, isLoading: reviewedMetricsLoading } = useQuery({
    queryKey: ['reviewed-metrics', id],
    queryFn: () => getReviewedMetrics(id),
  })

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
          <section className="card space-y-3" aria-label="Métricas analíticas revisadas">
            <div>
              <h2 className="font-semibold">Métricas analíticas revisadas</h2>
              <p className="text-xs text-gray-500">Solo observaciones activas, incluidas y confirmadas. Los conteos no implican una tasa de oportunidades.</p>
            </div>
            {reviewedMetricsLoading ? <p className="text-sm text-gray-400">Cargando métricas revisadas…</p> : (
              <>
                <ul className="grid gap-2 md:grid-cols-2">
                  {Object.entries(reviewedMetrics?.metrics ?? {}).map(([key, metric]) => <MetricContext key={key} metric={metric} />)}
                </ul>
                {!reviewedMetrics || Object.keys(reviewedMetrics.metrics).length === 0 ? <p className="text-sm text-gray-500">Todavía no hay observaciones analíticas revisadas.</p> : null}
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
                  <h3 className="font-semibold text-amber-900">Conciliación con planilla oficial</h3>
                  {reviewedMetrics?.official ? <>
                    <p className="mt-1 text-amber-900">Planilla oficial (snapshot {reviewedMetrics.official.snapshot_id}): {reviewedMetrics.official.home_score} - {reviewedMetrics.official.away_score}. La observación analítica no modifica estos valores.</p>
                    <ul className="mt-2 space-y-1 text-amber-900">
                      {reviewedMetrics.reconciliation.map(item => <li key={item.side}>
                        {item.side === 'home' ? homeName || 'Local' : awayName || 'Visitante'}: oficial {item.official} · analítico confirmado {item.analytical} · {item.discrepancy === 0 ? 'sin discrepancia' : `discrepancia ${item.discrepancy > 0 ? '+' : ''}${item.discrepancy}; revisar la evidencia analítica y su cobertura`}
                      </li>)}
                    </ul>
                  </> : <p className="mt-1 text-amber-900">No hay snapshot oficial para conciliar. Las métricas analíticas no sustituyen una planilla oficial.</p>}
                </div>
              </>
            )}
          </section>
          <PackageControls matchId={id} reviewedMetrics={reviewedMetrics?.metrics} />

          {/* Summary cards */}
          <div>
            <p className="mb-2 text-xs text-gray-500">Registro histórico sin revisión analítica ni conciliación oficial</p>
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

export default function StatisticsPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const id = Number(matchId)
  const navigate = useNavigate()
  const { data: match } = useQuery({ queryKey: ['match', id], queryFn: () => getMatch(id) })
  const { data: canonical, isLoading } = useQuery({ queryKey: ['canonical-metrics', id], queryFn: () => getCanonicalMetrics(id) })
  const { data: reconciliation } = useQuery({ queryKey: ['canonical-reconciliation', id], queryFn: () => getCanonicalReconciliation(id) })
  const warnings = useQuery({ queryKey: ['warnings-summary', id], queryFn: () => getWarningsSummary(id), enabled: Number.isInteger(id) && id > 0, retry: false })
  const eligibility = canonical?.eligibility
  const eventIds = Object.values(canonical?.metrics ?? {}).flatMap(metric => metric.evidence ?? []).map(item => item.event_id).filter((id, index, values) => values.indexOf(id) === index)

  if (isLoading) return <div className="p-4 text-gray-400">Cargando estadísticas canónicas…</div>
  return <div className="max-w-3xl mx-auto p-4 space-y-5">
    <div className="flex items-center gap-3">
      <button onClick={() => navigate(`/match/${id}/live`)} className="text-gray-400 hover:text-gray-700 p-1"><ChevronLeft size={24} /></button>
      <div><h1 className="text-xl font-bold text-gray-900">{match?.home_team?.name ?? '?'} vs {match?.away_team?.name ?? '?'}</h1><p className="text-sm text-gray-500">Estadísticas derivadas únicamente de evidencia canónica elegible.</p></div>
      <PdfReportExport matchId={id} />
    </div>
    <section className="card space-y-3" aria-label="Elegibilidad y métricas canónicas">
      <div><h2 className="font-semibold">Cobertura analítica</h2><p className="text-xs text-gray-500">Los registros desconocidos, no resueltos y con reloj no verificado se muestran como límites, no como afirmaciones tácticas.</p></div>
      <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-5"><span>Elegibles: {eligibility?.eligible ?? 0}</span><span>Excluidos: {eligibility?.excluded ?? 0}</span><span>Desconocidos: {eligibility?.unknown ?? 0}</span><span>No resueltos: {eligibility?.unresolved ?? 0}</span><span>Reloj no verificado: {eligibility?.clock_unverified ?? 0}</span></div>
      {eventIds.length === 0 && <p role="alert" className="rounded border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">No hay evidencia elegible; las conclusiones tácticas están bloqueadas.</p>}
      <ul className="grid gap-2 md:grid-cols-2">{Object.entries(canonical?.metrics ?? {}).map(([key, metric]) => <MetricContext key={key} metric={metric} />)}</ul>
    </section>
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm" aria-label="Conciliación con planilla oficial">
      <h2 className="font-semibold text-amber-900">Conciliación con planilla oficial inmutable</h2>
      {reconciliation?.official ? <><p className="mt-1">Snapshot {reconciliation.official.snapshot_id}: {reconciliation.official.home_score} - {reconciliation.official.away_score}. La analítica nunca modifica esta planilla.</p><ul className="mt-2">{reconciliation.reconciliation.map(item => <li key={item.side}>{item.side}: oficial {item.official} · analítico {item.analytical} · {item.discrepancy === 0 ? 'sin discrepancia' : `discrepancia ${item.discrepancy}`}</li>)}</ul>
        {reconciliation.discipline && reconciliation.discipline.length > 0 && <div className="mt-3 border-t border-amber-200 pt-2" aria-label="Conciliación de sanciones"><p className="font-semibold">Sanciones (amarillas / exclusiones / rojas)</p><ul className="mt-1">{reconciliation.discipline.map(item => <li key={item.side}>{item.side === 'home' ? match?.home_team?.name || 'Local' : match?.away_team?.name || 'Visitante'}: oficial {item.official.yellow}/{item.official.two_minute}/{item.official.red} vs observado {item.observed.yellow}/{item.observed.two_minute}/{item.observed.red} · {item.status === 'match' ? 'coincide' : 'discrepancia; revisar cobertura y evidencia'} ({item.coverage.eligible_discipline_events} eventos elegibles)</li>)}</ul></div>}
      </> : <p>No hay snapshot oficial; los datos analíticos no sustituyen resultados oficiales.</p>}
    </section>
    {warnings.isError ? <p role="alert" className="text-sm text-red-700">No se pudo cargar el resumen de advertencias.</p> : warnings.data && <WarningsPanel matchId={id} summary={warnings.data} />}
    <section className="card text-sm" aria-label="Evidencia canónica"><h2 className="font-semibold">Evidencia trazable</h2><p className="mt-1 text-gray-600">Eventos elegibles para este informe: {eventIds.length ? eventIds.map(eventId => `#${eventId}`).join(', ') : 'ninguno'}.</p></section>
    <PackageControls matchId={id} reviewedMetrics={canonical?.metrics} canonicalEventIds={eventIds} />
  </div>
}
