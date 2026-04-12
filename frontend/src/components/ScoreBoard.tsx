import { Play, Pause, RotateCcw, Plus, Minus } from 'lucide-react'
import type { useTimer } from '../hooks/useTimer'

interface Props {
  timer: ReturnType<typeof useTimer>
  homeTeam: string
  awayTeam: string
  homeScore: number
  awayScore: number
  period: 1 | 2
  onPeriodToggle: () => void
  onHomeAdjust: (delta: 1 | -1) => void
  onAwayAdjust: (delta: 1 | -1) => void
}

export default function ScoreBoard({
  timer, homeTeam, awayTeam, homeScore, awayScore,
  period, onPeriodToggle, onHomeAdjust, onAwayAdjust,
}: Props) {
  return (
    <div className="bg-gray-900 text-white rounded-2xl p-3 flex items-center gap-4">
      {/* Home */}
      <div className="flex-1 text-center">
        <p className="text-xs text-gray-400 truncate mb-1">{homeTeam}</p>
        <p className="text-4xl font-black tabular-nums">{homeScore}</p>
        <div className="flex justify-center gap-2 mt-1.5">
          <button
            onClick={() => onHomeAdjust(-1)}
            className="p-1 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-30"
            disabled={homeScore === 0}
          ><Minus size={12} /></button>
          <button
            onClick={() => onHomeAdjust(1)}
            className="p-1 rounded-lg bg-gray-700 hover:bg-gray-600"
          ><Plus size={12} /></button>
        </div>
      </div>

      {/* Timer block */}
      <div className="flex flex-col items-center gap-1.5 min-w-[110px]">
        <span className="text-3xl font-mono font-bold tabular-nums tracking-wider">
          {timer.format(timer.elapsed)}
        </span>
        <button
          onClick={onPeriodToggle}
          className="text-xs font-bold px-3 py-0.5 rounded-full bg-gray-700 hover:bg-gray-600 transition-colors"
        >
          {period === 1 ? '1er Tiempo' : '2do Tiempo'}
        </button>
        <div className="flex gap-2">
          <button
            onClick={timer.toggle}
            className={`p-2 rounded-xl transition-colors ${
              timer.running
                ? 'bg-yellow-400 text-gray-900 hover:bg-yellow-500'
                : 'bg-green-500 text-white hover:bg-green-600'
            }`}
          >
            {timer.running ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <button
            onClick={timer.reset}
            className="p-2 rounded-xl bg-gray-700 text-white hover:bg-gray-600"
          >
            <RotateCcw size={18} />
          </button>
        </div>
      </div>

      {/* Away */}
      <div className="flex-1 text-center">
        <p className="text-xs text-gray-400 truncate mb-1">{awayTeam}</p>
        <p className="text-4xl font-black tabular-nums">{awayScore}</p>
        <div className="flex justify-center gap-2 mt-1.5">
          <button
            onClick={() => onAwayAdjust(-1)}
            className="p-1 rounded-lg bg-gray-700 hover:bg-gray-600 disabled:opacity-30"
            disabled={awayScore === 0}
          ><Minus size={12} /></button>
          <button
            onClick={() => onAwayAdjust(1)}
            className="p-1 rounded-lg bg-gray-700 hover:bg-gray-600"
          ><Plus size={12} /></button>
        </div>
      </div>
    </div>
  )
}
