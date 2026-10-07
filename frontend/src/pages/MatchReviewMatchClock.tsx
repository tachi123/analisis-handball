interface MatchClockProps {
  session: any
  baselineClock: number | null
  map: any
  anchoredMap: any
  currentVideoTime: number
  saveSessionPending: boolean
}

export function MatchClock({ session, baselineClock, map, anchoredMap, currentVideoTime, saveSessionPending: _saveSessionPending }: MatchClockProps) {
  return (
    <section className="rounded border border-indigo-200 bg-indigo-50 p-3" aria-label="Reloj de partido">
      <p className="text-sm font-medium">Reloj de partido</p>
      {baselineClock === null ? <p className="text-lg font-semibold">Inicio del partido pendiente de confirmar</p> : <p className="font-mono text-4xl font-bold">{map.regulationSeconds === null ? '00:00' : `${String(Math.floor(map.regulationSeconds / 60)).padStart(2, '0')}:${String(map.regulationSeconds % 60).padStart(2, '0')}`}</p>}
      <p className="mt-1 text-xs text-gray-600">Posición de video: {currentVideoTime.toFixed(1)} s</p>
      {baselineClock === null ? (
        <>
          <p className="text-sm">Esta fuente de video necesita un saque inicial calibrado. Ubicala en el saque inicial y registrá primero su posesión antes de confirmar el reloj oficial.</p>
        </>
      ) : (
        <p className="text-xs text-indigo-900">Base inicial: video {session.clock_start_video_seconds?.toFixed(1)} s.{!anchoredMap.clockUnverified && ' La calibración avanzada está ajustando este tramo.'} La calibración avanzada es opcional.</p>
      )}
    </section>
  )
}
