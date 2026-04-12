import type { TagState } from '../types'
import type { useTagging } from '../hooks/useTagging'

const ACTIONS = ['Lanzamiento', 'Pérdida', 'Falta', '7 Metros']
const SHOT_RESULTS = ['Gol', 'Atajada', 'Fuera', 'Palo', 'Bloqueado', 'Gol (Arco Vacío)']
const SHOT_ZONES = ['6m', '9m', 'Extremo Iz', 'Extremo De', 'Penal', 'Contra']
const LOSS_DETAILS = ['Mal Pase', 'Pasos', 'Dobles', 'Robo', 'Pasivo', 'Fuera']
const FOUL_TYPES = ['Falta en Ataque', 'Falta Recibida 9m', 'Falta Recibida 7m', '+Sanción']
const SANCTION_TYPES = ['Amarilla', '2 Minutos', 'Roja', 'Azul']
const SANCTION_TARGETS = ['Jugador', 'Entrenador', 'Banco']

interface Props {
  tagging: ReturnType<typeof useTagging>
  onCommit: (state: TagState) => void
}

function BtnGroup({
  label,
  options,
  onSelect,
  cols = 2,
  colorFn,
}: {
  label: string
  options: string[]
  onSelect: (v: string) => void | TagState
  cols?: number
  colorFn?: (v: string) => string
}) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{label}</p>
      <div className={`grid gap-2 grid-cols-${cols}`}>
        {options.map(opt => (
          <button
            key={opt}
            onClick={() => onSelect(opt)}
            className={`py-3 px-2 rounded-xl font-semibold text-sm transition-all active:scale-95 border-2 ${
              colorFn ? colorFn(opt) : 'bg-white border-gray-200 text-gray-800 hover:bg-gray-50'
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function TaggingWizard({ tagging, onCommit }: Props) {
  const { state } = tagging

  const handleShotZone = (zone: string) => {
    const next = tagging.selectShotZone(zone)
    // If it's a goal, the wizard moves to 'assist' step — don't commit yet
    // If it's NOT a goal, the wizard moves to 'idle' — commit now
    if (next.step === 'idle') {
      onCommit(next)
    }
    // If step === 'assist', MatchLive handles it via PlayerGrid
  }

  const handleLoss = (detail: string) => {
    const next = tagging.selectLossDetail(detail)
    onCommit(next)
  }

  const handleFoul = (foulType: string) => {
    const next = tagging.selectFoulType(foulType)
    // If faultType requires no sanction flow, it returns a completed state
    if (next && typeof next === 'object' && 'step' in next && next.step === 'idle') {
      onCommit(next as TagState)
    }
  }

  const handleSanctionTarget = (target: string) => {
    const next = tagging.selectSanctionTarget(target)
    onCommit(next)
  }

  if (state.step === 'idle') {
    return (
      <p className="text-center text-gray-400 text-sm py-4">
        Seleccioná un jugador para registrar un evento
      </p>
    )
  }

  if (state.step === 'action') {
    return (
      <BtnGroup
        label="Acción"
        options={ACTIONS}
        cols={2}
        onSelect={tagging.selectAction}
        colorFn={v => ({
          Lanzamiento: 'bg-blue-50 border-blue-300 text-blue-800 hover:bg-blue-100',
          Pérdida: 'bg-red-50 border-red-300 text-red-800 hover:bg-red-100',
          Falta: 'bg-yellow-50 border-yellow-300 text-yellow-800 hover:bg-yellow-100',
          '7 Metros': 'bg-purple-50 border-purple-300 text-purple-800 hover:bg-purple-100',
        }[v] ?? 'bg-white border-gray-200 text-gray-800 hover:bg-gray-50')}
      />
    )
  }

  if (state.step === 'shot_result') {
    return (
      <BtnGroup
        label="Resultado del lanzamiento"
        options={SHOT_RESULTS}
        cols={3}
        onSelect={tagging.selectShotResult}
        colorFn={v =>
          v === 'Gol' || v === 'Gol (Arco Vacío)'
            ? 'bg-green-50 border-green-400 text-green-800 hover:bg-green-100'
            : 'bg-white border-gray-200 text-gray-800 hover:bg-gray-50'
        }
      />
    )
  }

  if (state.step === 'shot_zone') {
    return (
      <BtnGroup
        label="Zona de lanzamiento"
        options={SHOT_ZONES}
        cols={3}
        onSelect={handleShotZone}
      />
    )
  }

  if (state.step === 'loss_detail') {
    return (
      <BtnGroup
        label="Tipo de pérdida"
        options={LOSS_DETAILS}
        cols={3}
        onSelect={handleLoss}
      />
    )
  }

  if (state.step === 'foul_type') {
    return (
      <BtnGroup
        label="Tipo de falta"
        options={FOUL_TYPES}
        cols={2}
        onSelect={handleFoul}
      />
    )
  }

  if (state.step === 'sanction_type') {
    return (
      <BtnGroup
        label="Tipo de sanción"
        options={SANCTION_TYPES}
        cols={2}
        onSelect={tagging.selectSanctionType}
        colorFn={v => ({
          Amarilla: 'bg-yellow-100 border-yellow-400 text-yellow-800',
          '2 Minutos': 'bg-orange-100 border-orange-400 text-orange-800',
          Roja: 'bg-red-100 border-red-500 text-red-800',
          Azul: 'bg-blue-100 border-blue-400 text-blue-800',
        }[v] ?? 'bg-white border-gray-200 text-gray-800')}
      />
    )
  }

  if (state.step === 'sanction_target') {
    return (
      <BtnGroup
        label="¿Quién recibe la sanción?"
        options={SANCTION_TARGETS}
        cols={3}
        onSelect={handleSanctionTarget}
      />
    )
  }

  return null
}
