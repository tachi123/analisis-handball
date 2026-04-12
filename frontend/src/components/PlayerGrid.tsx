import type { MatchSquad } from '../types'

interface Props {
  squad: MatchSquad[]
  selectedId: number | null
  onSelect: (playerId: number) => void
}

const POSITION_COLOR: Record<string, string> = {
  PV: 'bg-yellow-100 border-yellow-400 text-yellow-800',
  CE: 'bg-blue-100 border-blue-400 text-blue-800',
  LI: 'bg-green-100 border-green-400 text-green-800',
  LD: 'bg-green-100 border-green-400 text-green-800',
  EXT: 'bg-purple-100 border-purple-400 text-purple-800',
}

export default function PlayerGrid({ squad, selectedId, onSelect }: Props) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {squad.map(sq => {
        const pos = sq.player?.global_position ?? ''
        const colorClass = POSITION_COLOR[pos] ?? 'bg-gray-100 border-gray-300 text-gray-800'
        const isSelected = sq.player_id === selectedId

        return (
          <button
            key={sq.player_id}
            onClick={() => onSelect(sq.player_id)}
            className={`
              flex flex-col items-center justify-center
              rounded-xl border-2 py-3 px-1
              font-bold transition-all duration-100 select-none
              active:scale-95
              ${colorClass}
              ${isSelected ? 'ring-4 ring-blue-500 scale-105' : 'hover:opacity-80'}
            `}
          >
            <span className="text-2xl leading-none">{sq.jersey_number}</span>
            <span className="text-xs mt-1 truncate max-w-full px-1 text-center leading-tight">
              {sq.player?.name.split(' ')[0] ?? '???'}
            </span>
            {pos && (
              <span className="text-[10px] opacity-60">{pos}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
