import type { GoalkeeperOriginZone } from '../types'

interface Props {
  value: GoalkeeperOriginZone | null
  onChange: (zone: GoalkeeperOriginZone) => void
}

interface ZoneShape {
  zone: GoalkeeperOriginZone
  d: string
  label: string
  labelX: number
  labelY: number
  labelRotate?: number
}

// Schematic top-down HALF court (goal at top). 6m/9m lines are flattened
// elliptical arcs centred on the goal mouth (cx=200, cy=14) so every zone
// stays a generous touch target. Draw order matters: later shapes win taps.
const ZONE_SHAPES: ZoneShape[] = [
  {
    zone: '9m_left',
    label: '9m',
    labelX: 72,
    labelY: 92,
    d: 'M50,14 A150,95 0 0 0 125,96.3 L112.5,135.2 A175,140 0 0 1 25,14 Z',
  },
  {
    zone: '9m_center',
    label: '',
    labelX: 0,
    labelY: 0,
    d: 'M125,96.3 A150,95 0 0 0 275,96.3 L287.5,135.2 A175,140 0 0 1 112.5,135.2 Z',
  },
  {
    zone: '9m_right',
    label: '9m',
    labelX: 328,
    labelY: 92,
    d: 'M275,96.3 A150,95 0 0 0 350,14 L375,14 A175,140 0 0 1 287.5,135.2 Z',
  },
  {
    zone: '6m_left',
    label: '',
    labelX: 0,
    labelY: 0,
    d: 'M200,14 L50,14 A150,95 0 0 0 125,96.3 Z',
  },
  {
    zone: '6m_center',
    label: '6m',
    labelX: 200,
    labelY: 76,
    d: 'M200,14 L125,96.3 A150,95 0 0 0 275,96.3 Z',
  },
  {
    zone: '6m_right',
    label: '',
    labelX: 0,
    labelY: 0,
    d: 'M200,14 L275,96.3 A150,95 0 0 0 350,14 Z',
  },
  {
    zone: 'wing_left',
    label: 'Extremos',
    labelX: 34,
    labelY: 148,
    labelRotate: -90,
    d: 'M10,14 L58,14 L58,250 L10,250 Z',
  },
  {
    zone: 'wing_right',
    label: 'Extremos',
    labelX: 366,
    labelY: 148,
    labelRotate: -90,
    d: 'M342,14 L390,14 L390,250 L342,250 Z',
  },
  {
    zone: 'counter',
    label: 'Contra',
    labelX: 200,
    labelY: 284,
    d: 'M10,262 L390,262 L390,296 L10,296 Z',
  },
  // Penalty spot sits inside/below the 6m line, above the 9m centre band.
  {
    zone: 'seven_meter',
    label: 'Penal',
    labelX: 200,
    labelY: 121,
    d: 'M164,116 A36,26 0 0 0 236,116 A36,26 0 0 0 164,116 Z',
  },
]

const BASE_FILL: Record<GoalkeeperOriginZone, string> = {
  '6m_left': '#e0e7ff',
  '6m_center': '#e0e7ff',
  '6m_right': '#e0e7ff',
  '9m_left': '#f1f5f9',
  '9m_center': '#f1f5f9',
  '9m_right': '#f1f5f9',
  wing_left: '#f1f5f9',
  wing_right: '#f1f5f9',
  seven_meter: '#ffedd5',
  counter: '#f1f5f9',
}

export default function GkCourtPicker({ value, onChange }: Props) {
  return (
    <svg viewBox="0 0 400 300" className="w-full h-auto select-none" role="group" aria-label="Zona de lanzamiento">
      <rect x={10} y={14} width={380} height={282} rx={6} fill="#ffffff" stroke="#cbd5e1" strokeWidth={2} />
      <rect x={172} y={4} width={56} height={10} fill="#334155" />

      {ZONE_SHAPES.map(({ zone, d }) => {
        const selected = value === zone
        return (
          <path
            key={zone}
            d={d}
            fill={selected ? '#2563eb' : BASE_FILL[zone]}
            stroke={selected ? '#1d4ed8' : '#94a3b8'}
            strokeWidth={selected ? 2.5 : 1.5}
            className="cursor-pointer transition-opacity duration-100 hover:opacity-80"
            role="button"
            aria-pressed={selected}
            aria-label={zone}
            onClick={() => onChange(zone)}
          />
        )
      })}

      {ZONE_SHAPES.filter(({ label }) => label).map(({ zone, label, labelX, labelY, labelRotate }) => (
        <text
          key={`label-${zone}`}
          x={labelX}
          y={labelY}
          transform={labelRotate ? `rotate(${labelRotate} ${labelX} ${labelY})` : undefined}
          textAnchor="middle"
          fontSize={12}
          fontWeight={700}
          fill={value === zone ? '#ffffff' : '#64748b'}
          pointerEvents="none"
        >
          {label}
        </text>
      ))}
    </svg>
  )
}
