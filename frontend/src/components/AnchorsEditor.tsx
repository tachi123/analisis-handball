import { useState } from 'react'
import type { TimeAnchor } from '../types'

type DraftAnchor = Omit<TimeAnchor, 'id'>
type Props = { anchors: TimeAnchor[]; currentVideoTime: number; onSave: (anchors: DraftAnchor[]) => void; saving?: boolean; error?: string }

const blank = (): DraftAnchor => ({ period: 1, video_seconds: 0, regulation_seconds: 0, uncertainty_seconds: 0 })

export default function AnchorsEditor({ anchors, currentVideoTime, onSave, saving, error }: Props) {
  const [items, setItems] = useState<DraftAnchor[]>(() => anchors.map(anchor => ({ period: anchor.period, video_seconds: anchor.video_seconds, regulation_seconds: anchor.regulation_seconds, uncertainty_seconds: anchor.uncertainty_seconds })))
  const update = (index: number, field: keyof DraftAnchor, value: number) => setItems(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item))
  return <section className="card space-y-3" aria-label="Anclajes de tiempo">
    <div className="flex items-center justify-between"><h2 className="font-semibold">Calibrar reloj</h2><button className="btn" onClick={() => setItems(current => [...current, { ...blank(), video_seconds: currentVideoTime }])}>Agregar anclaje</button></div>
    <p className="text-sm text-gray-600">Ingresá el tiempo reglamentario de inicio o la referencia observada. Un anclaje solo permite buscar; dos anclajes válidos del mismo período verifican un tramo.</p>
    {items.map((anchor, index) => <div key={index} className="grid grid-cols-2 gap-2 rounded border p-2 text-sm">
      <label>Período<input aria-label={`Período ${index + 1}`} className="review-target ml-1 w-16 rounded border p-1" type="number" min="1" value={anchor.period} onChange={e => update(index, 'period', Number(e.target.value))} /></label>
      <label>Tiempo reglamentario<input aria-label={`Tiempo reglamentario ${index + 1}`} className="review-target ml-1 w-20 rounded border p-1" type="number" min="0" value={anchor.regulation_seconds} onChange={e => update(index, 'regulation_seconds', Number(e.target.value))} /></label>
      <label>Video<input aria-label={`Tiempo de video ${index + 1}`} className="review-target ml-1 w-20 rounded border p-1" type="number" min="0" value={anchor.video_seconds} onChange={e => update(index, 'video_seconds', Number(e.target.value))} /></label>
      <button className="btn text-sm" onClick={() => update(index, 'video_seconds', currentVideoTime)}>Usar posición actual</button>
      <button className="review-target text-left text-sm text-red-700 underline" onClick={() => setItems(current => current.filter((_, itemIndex) => itemIndex !== index))}>Eliminar</button>
    </div>)}
    <button className="btn btn-primary min-h-11 w-full" disabled={saving} onClick={() => onSave(items)}> {saving ? 'Guardando…' : 'Guardar anclajes'}</button>
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
  </section>
}
