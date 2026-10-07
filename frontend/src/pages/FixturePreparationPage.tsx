import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronLeft, FileText, Play, UserCheck, UserX } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { enableCanonicalAnalysis, getOfficialSheet, getOfficialSheetPdf, getPreloadedFixture, saveAnalysisSession } from '../api/client'
import type { AnalysisProfile } from '../types'

const profiles: Array<{ value: AnalysisProfile; name: string; detail: string }> = [
  { value: 'complete', name: 'Completo', detail: 'Incidencias, contexto de equipo y revisión integral.' },
  { value: 'classic', name: 'Clásico', detail: 'Marcado general de incidencias del partido.' },
  { value: 'goalkeepers', name: 'Arqueros', detail: 'Foco en tiros y acciones de arqueros.' },
]

export default function FixturePreparationPage() {
  const { fixtureKey = '' } = useParams()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<AnalysisProfile>('complete')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const fixtureQuery = useQuery({ queryKey: ['preloaded-fixture', fixtureKey], queryFn: () => getPreloadedFixture(fixtureKey), enabled: Boolean(fixtureKey) })
  const matchId = fixtureQuery.data?.linked_match_id
  const sheetQuery = useQuery({ queryKey: ['official-sheet', matchId], queryFn: () => getOfficialSheet(matchId!), enabled: Boolean(matchId), retry: false })
  const [selectedPlayers, setSelectedPlayers] = useState<Set<string>>(new Set())
  const start = useMutation({
    mutationFn: async () => {
      await enableCanonicalAnalysis(matchId!)
      return saveAnalysisSession(matchId!, { mode: 'video', profile, source: null, video_position_seconds: null, clock_start_video_seconds: null, angle: null, filters: {}, draft: {}, queue: [], anchors: [], time_segments: [] })
    },
    onSuccess: () => navigate(`/match/${matchId}/review`),
  })
  const pdf = useMutation({ mutationFn: () => getOfficialSheetPdf(matchId!), onSuccess: blob => setPdfUrl(current => { if (current) URL.revokeObjectURL(current); return URL.createObjectURL(blob) }) })
  useEffect(() => () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl) }, [pdfUrl])

  if (fixtureQuery.isLoading || sheetQuery.isLoading) return <main className="p-4">Cargando preparación del partido…</main>
  if (fixtureQuery.isError || !fixtureQuery.data) return <main className="p-4 text-red-700" role="alert">No se pudo cargar el fixture preimportado.</main>
  if (!matchId || sheetQuery.isError || !sheetQuery.data) return <main className="p-4 text-amber-800" role="alert">Este fixture no tiene una planilla oficial confirmada disponible para preparar el análisis.</main>
  const fixture = fixtureQuery.data
  const sheet = sheetQuery.data
  const unresolved = fixture.unresolved_roster_players

  const togglePlayer = (side: 'home' | 'away', jersey: number, name: string) => {
    const key = `${side}-${jersey}-${name}`
    setSelectedPlayers(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const isPlayerSelected = (side: 'home' | 'away', jersey: number, name: string) => {
    return selectedPlayers.has(`${side}-${jersey}-${name}`)
  }

  return <main className="mx-auto max-w-5xl space-y-5 p-4">
    <header className="flex flex-wrap items-center gap-3"><Link className="btn btn-ghost" to="/matches"><ChevronLeft size={16} /> Partidos</Link><div><h1 className="text-2xl font-bold">Preparar análisis</h1><p className="text-sm text-gray-600">Planilla oficial importada. Esta pantalla es de sólo lectura.</p></div></header>
    <section className="card space-y-3" aria-labelledby="fixture-context"><h2 id="fixture-context" className="text-lg font-semibold">Contexto oficial</h2><p className="text-xl font-semibold">{sheet.home.name} {sheet.home.score} - {sheet.away.score} {sheet.away.name}</p><p className="text-sm text-gray-600">{fixture.stage.name} · {fixture.scheduled_date ?? 'Fecha no informada'} · {fixture.venue ?? 'Sede no informada'}</p><p className="text-xs text-gray-500">Fuente: {sheet.provenance.filename} · {sheet.provenance.page_count} página(s)</p>{sheet.pdf_available ? <button className="btn" onClick={() => pdf.mutate()} disabled={pdf.isPending}><FileText size={16} /> {pdf.isPending ? 'Abriendo PDF…' : 'Ver PDF oficial'}</button> : <p className="text-sm text-amber-800">El PDF original no está disponible en este entorno; los datos importados siguen siendo oficiales.</p>}{pdf.isError && <p className="text-sm text-red-700" role="alert">No se pudo abrir el PDF oficial.</p>}{pdfUrl && <section className="space-y-2"><button className="btn" onClick={() => setPdfUrl(current => { if (current) URL.revokeObjectURL(current); return null })}>Cerrar PDF</button><iframe className="h-[32rem] w-full border" title="Planilla oficial" src={pdfUrl} /></section>}</section>
    <section className="grid gap-3 md:grid-cols-2" aria-label="Planteles y estadísticas importados">{([['home', sheet.home, 'Local'], ['away', sheet.away, 'Visitante']] as const).map(([sideKey, team, sideLabel]) => <article key={sideKey} className="card"><div className="flex items-center justify-between"><h2 className="font-semibold">{sideLabel}: {team.name}</h2><span className="text-sm text-gray-600">Marcador: {team.score}</span></div><div className="mt-2 overflow-x-auto"><table className="w-full text-sm" role="grid"><thead><tr className="border-b text-left text-gray-500"><th className="p-2 w-8">#</th><th className="p-2">Jugador</th><th className="p-2 w-16">G</th><th className="p-2 w-16">A</th><th className="p-2 w-16">2'</th><th className="p-2 w-16">R</th><th className="p-2 w-10"></th></tr></thead><tbody>{team.players.map((player, idx) => <tr key={`${sideKey}-${player.jersey_number}-${player.name}`} className={`${idx % 2 === 0 ? 'bg-gray-50' : ''} ${isPlayerSelected(sideKey as 'home' | 'away', player.jersey_number, player.name) ? 'bg-indigo-50' : ''} hover:bg-gray-100 cursor-pointer transition-colors`} onClick={() => togglePlayer(sideKey as 'home' | 'away', player.jersey_number, player.name)}><td className="p-2 font-mono text-gray-700">#{player.jersey_number}</td><td className="p-2 truncate max-w-xs">{player.name}</td><td className="p-2 text-center font-medium">{player.official_goals}</td><td className="p-2 text-center text-gray-600">{player.official_yellow}</td><td className="p-2 text-center text-amber-700">{player.official_2min}</td><td className="p-2 text-center text-red-700">{player.official_red}</td><td className="p-2 text-center"><span title={player.player_id ? 'Identidad resuelta' : 'Identidad pendiente'}>{player.player_id ? <UserCheck className="w-4 h-4 text-green-600 mx-auto" /> : <UserX className="w-4 h-4 text-amber-600 mx-auto" />}</span></td></tr>)}</tbody></table></div><p className="mt-2 text-xs text-gray-500">Click en una fila para preseleccionar jugador en análisis por equipo. {team.players.filter(p => !p.player_id).length} sin identidad resuelta.</p></article>)}</section>
    {unresolved > 0 && <section className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950" role="status"><b>Identidades de jugadores pendientes.</b> Hay {unresolved} ficha(s) oficiales sin identidad local resuelta. Los jugadores de la planilla están disponibles para análisis por equipo (sin atribución individual) hasta resolver las identidades.</section>}
    <section className="card space-y-3" aria-labelledby="profile-heading"><h2 id="profile-heading" className="text-lg font-semibold">Iniciar análisis de video</h2><p className="text-sm text-gray-600">Elegí el perfil antes de adjuntar el video. No se inicia ningún análisis hasta confirmar esta acción.</p><fieldset className="grid gap-2 md:grid-cols-3"><legend className="sr-only">Perfil de análisis</legend>{profiles.map(item => <label key={item.value} className={`cursor-pointer rounded-xl border p-3 ${profile === item.value ? 'border-indigo-600 bg-indigo-50' : 'bg-white'}`}><input className="mr-2" type="radio" name="profile" value={item.value} checked={profile === item.value} onChange={() => setProfile(item.value)} /><b>{item.name}</b><span className="mt-1 block text-sm text-gray-600">{item.detail}</span></label>)}</fieldset><button className="btn btn-primary min-h-11" onClick={() => start.mutate()} disabled={start.isPending}><Play size={16} /> {start.isPending ? 'Iniciando…' : 'Iniciar análisis y adjuntar video'}</button>{start.isError && <p role="alert" className="text-sm text-red-700">No se pudo iniciar el análisis: {start.error instanceof Error ? start.error.message : 'revisá la planilla oficial e intentá nuevamente.'}</p>}</section>
  </main>
}
