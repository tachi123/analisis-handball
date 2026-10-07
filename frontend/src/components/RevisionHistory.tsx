import type { CanonicalEvent } from '../types'

export default function RevisionHistory({ event }: { event: CanonicalEvent | null }) {
  return <section className="card space-y-2" aria-label="Detalle de revisión">
    <h2 className="font-semibold">Última revisión</h2>
    {event ? <><p className="text-sm">Motivo: {event.reason ?? 'No informado'}</p><p className="text-sm">Evidencia: {event.evidence?.map(item => item.kind).join(', ') || 'sin evidencia'}</p></> : <p className="text-sm text-gray-500">Seleccioná un evento para revisar sus datos disponibles.</p>}
    <p className="rounded bg-amber-50 p-2 text-xs text-amber-900">El historial cronológico, los diffs, confidence, visibility y payloads corregidos requieren un contrato de backend futuro; no se muestran como datos persistidos.</p>
  </section>
}
