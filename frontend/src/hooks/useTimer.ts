import { useEffect, useRef, useState } from 'react'

export function useTimer() {
  const [elapsed, setElapsed] = useState(0) // seconds
  const [running, setRunning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(0)
  const accumulatedRef = useRef<number>(0)

  useEffect(() => {
    if (running) {
      startTimeRef.current = Date.now()
      intervalRef.current = setInterval(() => {
        setElapsed(accumulatedRef.current + Math.floor((Date.now() - startTimeRef.current) / 1000))
      }, 500)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [running])

  const start = () => {
    if (!running) setRunning(true)
  }

  const pause = () => {
    if (running) {
      accumulatedRef.current = elapsed
      setRunning(false)
    }
  }

  const reset = () => {
    setRunning(false)
    setElapsed(0)
    accumulatedRef.current = 0
  }

  const toggle = () => (running ? pause() : start())

  const format = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0')
    const sec = (s % 60).toString().padStart(2, '0')
    return `${m}:${sec}`
  }

  return { elapsed, running, start, pause, reset, toggle, format }
}
