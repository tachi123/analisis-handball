interface Props {
  homeTeam: string
  awayTeam: string
  possession: string // team name
  onSwitch: () => void
}

export default function PossessionBar({ homeTeam, possession, onSwitch }: Props) {
  const isHome = possession === homeTeam

  return (
    <button
      onClick={onSwitch}
      className={`w-full rounded-xl py-3 px-4 font-bold text-white text-sm transition-colors ${
        isHome ? 'bg-blue-600 hover:bg-blue-700' : 'bg-red-600 hover:bg-red-700'
      }`}
    >
      <span className="opacity-75 mr-2">POSESIÓN:</span>
      {possession}
      <span className="ml-2 text-xs opacity-75">(toca para cambiar)</span>
    </button>
  )
}
