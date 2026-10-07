import type { ShotZone } from '../types'

interface Props {
  value: ShotZone | null
  onChange: (zone: ShotZone) => void
}

const zones = [1, 2, 3, 4, 5, 6, 7, 8, 9] as ShotZone[]

/** IHF goal-target picker. Values are target cells, never legacy shot origins. */
export default function GkCourtPicker({ value, onChange }: Props) {
  return <div className="grid grid-cols-3 gap-1" role="group" aria-label="Zona objetivo IHF">
    {zones.map(zone => <button key={zone} type="button" aria-pressed={value === zone} aria-label={`Zona IHF ${zone}`} onClick={() => onChange(zone)} className={`min-h-11 rounded border font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700 ${value === zone ? 'border-indigo-700 bg-indigo-600 text-white' : 'border-slate-300 bg-slate-50 text-slate-800'}`}>{zone}</button>)}
  </div>
}
