import { useEffect, useState } from 'react'

export type LiveClockCheckpoint = { elapsedSeconds: number; running: boolean; savedAtMs: number }
const elapsed = (checkpoint: LiveClockCheckpoint) => checkpoint.running ? checkpoint.elapsedSeconds + Math.max(0, Math.floor((Date.now() - checkpoint.savedAtMs) / 1000)) : checkpoint.elapsedSeconds

export function useLiveClock(period: number, initial: LiveClockCheckpoint | undefined, onCheckpoint: (checkpoint: LiveClockCheckpoint) => void) {
  const [checkpoint, setCheckpoint] = useState<LiveClockCheckpoint>(initial ?? { elapsedSeconds: 0, running: false, savedAtMs: Date.now() })
  const [now, setNow] = useState(Date.now())

  useEffect(() => { setCheckpoint(initial ?? { elapsedSeconds: 0, running: false, savedAtMs: Date.now() }); setNow(Date.now()) }, [period, initial?.elapsedSeconds, initial?.running, initial?.savedAtMs])

  useEffect(() => {
    if (!checkpoint.running) return
    const timer = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(timer)
  }, [checkpoint.running])

  const update = (next: LiveClockCheckpoint) => { setCheckpoint(next); onCheckpoint(next) }
  const seconds = checkpoint.running ? checkpoint.elapsedSeconds + Math.max(0, Math.floor((now - checkpoint.savedAtMs) / 1000)) : checkpoint.elapsedSeconds
  return { elapsedSeconds: seconds, running: checkpoint.running,
    start: () => update({ elapsedSeconds: elapsed(checkpoint), running: true, savedAtMs: Date.now() }),
    pause: () => update({ elapsedSeconds: elapsed(checkpoint), running: false, savedAtMs: Date.now() }),
    reset: () => update({ elapsedSeconds: 0, running: false, savedAtMs: Date.now() }), }
}
