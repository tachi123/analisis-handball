import AnchorsEditor from '../components/AnchorsEditor'
import RevisionHistory from '../components/RevisionHistory'
import PersistedReviewState from '../components/PersistedReviewState'

interface SidebarProps {
  officialQuery: any
  session: any
  draft: any
  queue: any
  anchorsOpen: boolean
  setAnchorsOpen: (v: boolean) => void
  anchorSave: any
  sessionId: number
}

export function Sidebar({ officialQuery, session, draft, queue, anchorsOpen, setAnchorsOpen, anchorSave, sessionId: _sessionId }: SidebarProps) {
  return (
    <aside className="space-y-3" id="review-anchors">
      {officialQuery.data && <section className="card" aria-label="Contexto oficial"><h2 className="font-semibold">Contexto oficial</h2><p className="mt-1 text-sm">{officialQuery.data.home.name} {officialQuery.data.home.score} - {officialQuery.data.away.score} {officialQuery.data.away.name}</p><p className="mt-1 text-xs text-gray-500">{officialQuery.data.provenance.filename} · {officialQuery.data.home.players.length + officialQuery.data.away.players.length} jugadores importados</p></section>}
      {officialQuery.isError && !isNotFound(officialQuery.error) && <section role="alert" className="card border-red-300 text-red-700"><h2 className="font-semibold">No se pudo cargar la planilla oficial</h2><p className="mt-1 text-sm">{message(officialQuery.error)}</p><button className="btn mt-3" onClick={() => officialQuery.refetch()}>Reintentar cargar planilla</button></section>}
      <PersistedReviewState draft={draft} queue={queue} />
      <section className="card">
        <button className="btn min-h-11 w-full" aria-expanded={anchorsOpen} onClick={() => setAnchorsOpen(!anchorsOpen)}>{anchorsOpen ? 'Ocultar calibración avanzada' : 'Mostrar calibración avanzada'}</button>
        <p className="mt-2 text-xs text-gray-600">Opcional: usala para corregir cortes, repeticiones o desajustes; el comienzo del reloj alcanza para el análisis habitual.</p>
        {anchorsOpen && <div className="mt-3"><AnchorsEditor anchors={session.anchors} currentVideoTime={0} onSave={anchors => anchorSave.mutate(anchors)} saving={anchorSave.isPending} error={anchorSave.isError ? message(anchorSave.error) : undefined} /></div>}
      </section>
      <RevisionHistory event={null} />
    </aside>
  )
}

const message = (error: unknown) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : error instanceof Error ? error.message : 'Error de red o validación'
}

const isNotFound = (error: unknown) => (error as { response?: { status?: number } })?.response?.status === 404
