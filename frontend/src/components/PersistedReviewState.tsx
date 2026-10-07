import type { AnalysisSession } from '../types'

export default function PersistedReviewState({ draft, queue }: Pick<AnalysisSession, 'draft' | 'queue'>) {
  const draftEntries = Object.entries(draft)
  return <section className="card" aria-label="Estado persistido de revisión">
    <h2 className="font-semibold">Borrador y cola guardados</h2>
    <div className="mt-2 space-y-3 text-sm">
      <section aria-labelledby="persisted-draft-heading">
        <h3 id="persisted-draft-heading" className="font-medium">Borrador persistido</h3>
        {draftEntries.length === 0 ? <p className="text-gray-600">No hay un borrador guardado para esta revisión.</p> : <dl className="mt-1 space-y-1 rounded bg-gray-50 p-2">{draftEntries.map(([key, value]) => <div key={key}><dt className="inline font-medium">{key}: </dt><dd className="inline break-words">{typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)}</dd></div>)}</dl>}
      </section>
      <section aria-labelledby="persisted-queue-heading">
        <h3 id="persisted-queue-heading" className="font-medium">Cola de revisión</h3>
        {queue.length === 0 ? <p className="text-gray-600">No hay elementos pendientes en la cola de revisión.</p> : <ol className="mt-1 list-decimal space-y-1 pl-5">{queue.map((item, index) => <li key={index} className="break-words">{JSON.stringify(item)}</li>)}</ol>}
      </section>
    </div>
  </section>
}