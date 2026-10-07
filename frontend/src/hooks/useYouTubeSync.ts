import { useCallback, useEffect, useRef, useState } from 'react'
import type { VideoAvailabilityState, VideoSource } from '../types'
import { playerAvailability } from '../videoReview'
import { loadYouTubeIframeApi, type YouTubePlayer } from '../youtubeIframeApi'

type SourceTimestamp = { sourceId: number; time: number; observedAt: number }

export type SyncState = {
  playerRef: React.RefObject<HTMLDivElement>
  currentTime: number
  isPlaying: boolean
  availability: VideoAvailabilityState
  seekTo: (seconds: number) => void
  play: () => void
  pause: () => void
  retry: () => void
  pauseAndReadCurrentTime: () => Promise<number>
  setCurrentTimeManual: (time: number) => void
}

const PLAYING = 1
const PAUSED = 2
const ENDED = 0
const CUED = 5
const PAUSE_TIMEOUT_MS = 2000
const RECENT_TIMESTAMP_MS = 5000

export function useYouTubeSync(source: VideoSource | null, initialTime = 0): SyncState {
  const sourceIdentity = source ? `${source.id}:${source.provider}:${source.provider_video_id}` : null
  const sourceSnapshot = useRef(source)
  const initialTimeSnapshot = useRef(initialTime)
  sourceSnapshot.current = source
  initialTimeSnapshot.current = initialTime
  const playerRef = useRef<HTMLDivElement>(null)
  const player = useRef<YouTubePlayer | null>(null)
  const interval = useRef<number | null>(null)
  const timestamp = useRef<SourceTimestamp | null>(null)
  const sourceId = useRef<number | null>(source?.id ?? null)
  const playing = useRef(false)
  const pendingPauseRead = useRef<{ timeout: number; resolve: (time: number) => void; reject: (error: Error) => void } | null>(null)
  const [currentTime, setCurrentTime] = useState(initialTime)
  const [isPlaying, setIsPlaying] = useState(false)
  const [availability, setAvailability] = useState<VideoAvailabilityState>(source?.availability_state ?? 'unavailable')
  const [retryGeneration, setRetryGeneration] = useState(0)

  const stopPolling = useCallback(() => {
    if (interval.current !== null) window.clearInterval(interval.current)
    interval.current = null
  }, [])

  const observeTime = useCallback((): number | null => {
    try {
      const time = player.current?.getCurrentTime()
      if (typeof time !== 'number' || !Number.isFinite(time) || sourceId.current === null) return null
      setCurrentTime(time)
      timestamp.current = { sourceId: sourceId.current, time, observedAt: Date.now() }
      return time
    } catch {
      return null
    }
  }, [])

  const settleWithCurrentTime = useCallback((resolve: (time: number) => void, reject: (error: Error) => void) => {
    const direct = observeTime()
    if (direct !== null) {
      resolve(direct)
      return
    }
    const fallback = timestamp.current
    if (fallback?.sourceId === sourceId.current && Date.now() - fallback.observedAt <= RECENT_TIMESTAMP_MS && Number.isFinite(fallback.time)) {
      resolve(fallback.time)
      return
    }
    reject(new Error('La sincronización con YouTube no está disponible; no se pudo leer la posición actual.'))
  }, [observeTime])

  const destroyPlayer = useCallback((reason: string) => {
    stopPolling()
    playing.current = false
    player.current?.destroy()
    player.current = null
    const pending = pendingPauseRead.current
    if (pending) {
      window.clearTimeout(pending.timeout)
      pendingPauseRead.current = null
      pending.reject(new Error(reason))
    }
  }, [stopPolling])

  useEffect(() => {
    const activeSource = sourceSnapshot.current
    const sourceInitialTime = initialTimeSnapshot.current
    sourceId.current = activeSource?.id ?? null
    timestamp.current = null
    playing.current = false
    setIsPlaying(false)
    setCurrentTime(sourceInitialTime)
    setAvailability(activeSource?.availability_state ?? 'unavailable')
    if (!activeSource || !playerRef.current) return

    let disposed = false
    const startPolling = () => {
      stopPolling()
      interval.current = window.setInterval(observeTime, 500)
    }
    const finishPauseRead = () => {
      const pending = pendingPauseRead.current
      if (!pending) return
      window.clearTimeout(pending.timeout)
      pendingPauseRead.current = null
      settleWithCurrentTime(pending.resolve, pending.reject)
    }
    loadYouTubeIframeApi().then(YT => {
      if (disposed || !playerRef.current) return
      player.current = new YT.Player(playerRef.current, {
        videoId: activeSource.provider_video_id,
        // youtube-nocookie is a documented Player host and preserves the existing privacy-enhanced embed behavior.
        host: 'https://www.youtube-nocookie.com',
        playerVars: { enablejsapi: 1, playsinline: 1, origin: window.location.origin, ...(sourceInitialTime > 0 ? { start: Math.floor(sourceInitialTime) } : {}) },
        events: {
          onReady: () => {
            if (disposed) return
            setAvailability('ready')
            observeTime()
          },
          onStateChange: ({ data }) => {
            if (disposed) return
            const nowPlaying = data === PLAYING
            playing.current = nowPlaying
            setIsPlaying(nowPlaying)
            if (nowPlaying) {
              observeTime()
              startPolling()
              return
            }
            stopPolling()
            if (data === CUED || data === PAUSED || data === ENDED) observeTime()
            if (data === PAUSED) finishPauseRead()
          },
          onError: ({ data }) => {
            if (disposed) return
            disposed = true
            destroyPlayer('El reproductor de YouTube dejó de estar disponible antes de terminar la lectura.')
            setAvailability(playerAvailability(data))
          },
        },
      })
    }).catch(() => {
      if (!disposed) setAvailability('player_error')
    })
    return () => {
      disposed = true
      destroyPlayer('El reproductor de YouTube fue reemplazado antes de terminar la lectura.')
    }
  }, [destroyPlayer, observeTime, retryGeneration, settleWithCurrentTime, sourceIdentity, stopPolling])

  const seekTo = useCallback((seconds: number) => player.current?.seekTo(Math.max(0, seconds), true), [])
  const play = useCallback(() => player.current?.playVideo(), [])
  const pause = useCallback(() => player.current?.pauseVideo(), [])
  const retry = useCallback(() => setRetryGeneration(generation => generation + 1), [])
  const pauseAndReadCurrentTime = useCallback(() => new Promise<number>((resolve, reject) => {
    if (!player.current) {
      settleWithCurrentTime(resolve, reject)
      return
    }
    let state: number
    try {
      state = player.current.getPlayerState()
    } catch {
      settleWithCurrentTime(resolve, reject)
      return
    }
    if (state !== PLAYING && !playing.current) {
      settleWithCurrentTime(resolve, reject)
      return
    }
    if (pendingPauseRead.current) {
      reject(new Error('Ya se está leyendo la posición del video.'))
      return
    }
    const timeout = window.setTimeout(() => {
      const pending = pendingPauseRead.current
      if (!pending || pending.timeout !== timeout) return
      pendingPauseRead.current = null
      settleWithCurrentTime(resolve, reject)
    }, PAUSE_TIMEOUT_MS)
    pendingPauseRead.current = { timeout, resolve, reject }
    player.current.pauseVideo()
  }), [settleWithCurrentTime])
  const setCurrentTimeManual = useCallback((time: number) => setCurrentTime(Math.max(0, time)), [])

  return { playerRef, currentTime, isPlaying, availability, seekTo, play, pause, retry, pauseAndReadCurrentTime, setCurrentTimeManual }
}
