import { useState } from 'react'
import { checkpoint, message, replaceVideoSource } from '../pages/MatchReview'

export function parseVideoPosition(value: string): number | null {
  const input = value.trim()
  if (/^\d+(?:\.\d+)?$/.test(input)) {
    const seconds = Number(input)
    return Number.isFinite(seconds) && seconds >= 0 ? seconds : null
  }
  const match = /^(\d+):(\d{1,2}(?:\.\d+)?)$/.exec(input)
  if (!match) return null
  const minutes = Number(match[1]); const seconds = Number(match[2])
  return Number.isFinite(minutes) && Number.isFinite(seconds) && seconds >= 0 && seconds < 60 ? minutes * 60 + seconds : null
}

interface VideoSectionProps {
  session: any
  player: any
  playerUnavailable: boolean
  saveSession: any
  sessionQuery: any
  sourceUrl: string
  setSourceUrl: (v: string) => void
  setSourceError: (v: string) => void
  sourceError: string
  saveSessionPending: boolean
  setNotice: (v: string) => void
  supportedYouTubeUrl: (v: string) => boolean
}

export function VideoSection({ session, player, playerUnavailable, saveSession, sessionQuery, sourceUrl, setSourceUrl, setSourceError, sourceError, saveSessionPending, setNotice, supportedYouTubeUrl }: VideoSectionProps) {
  const [adjustingPosition, setAdjustingPosition] = useState(false)
  const [manualPosition, setManualPosition] = useState('')
  const [manualPositionError, setManualPositionError] = useState('')
  const saveManualPosition = () => {
    const seconds = parseVideoPosition(manualPosition)
    if (seconds === null) {
      setManualPositionError('Ingresá una posición de video válida en segundos o mm:ss, sin valores negativos.')
      return
    }
    setManualPositionError('')
    player.setCurrentTimeManual(seconds)
    saveSession.mutate(checkpoint(session, { video_position_seconds: seconds }))
    setNotice(`Posición de video ajustada a ${seconds.toFixed(1)} s.`)
    setAdjustingPosition(false)
  }
  const manualPositionControl = <div className="mt-2">
    <button className="btn" onClick={() => { setAdjustingPosition(open => !open); setManualPositionError('') }}>Ajustar posición de video</button>
    {adjustingPosition && <div className="mt-2 rounded border p-2"><label className="block text-sm">Posición de video (mm:ss o segundos)<input className="review-target mt-1 w-full rounded border p-2" value={manualPosition} onChange={event => { setManualPosition(event.target.value); setManualPositionError('') }} placeholder="01:23 o 83" /></label>{manualPositionError && <p role="alert" className="mt-1 text-sm text-red-700">{manualPositionError}</p>}<div className="mt-2 flex gap-2"><button className="btn btn-primary" disabled={saveSessionPending} onClick={saveManualPosition}>Guardar posición de video</button><button className="btn" onClick={() => setAdjustingPosition(false)}>Cancelar</button></div></div>}
  </div>
  // The IFrame API requires a layoutable, stable mount even while recovery UI is shown.
  const playerMount = <div ref={player.playerRef} className="mt-2 aspect-video w-full" title="Video del partido" />
  if (playerUnavailable) {
    return (
      <>{playerMount}<div role="alert" className="mt-2 rounded bg-amber-50 p-3">
        <b>Reproducción no disponible.</b>
        <p className="text-sm">Podés conservar una posición manual de video para revisar evidencia, aunque YouTube no pueda sincronizarse.</p>
        <p className="mt-1 text-xs text-gray-600">Posición de video: {player.currentTime.toFixed(1)} s</p>
        {session.source && <button className="btn mt-2" onClick={() => window.open(session.source!.original_url, '_blank', 'noopener,noreferrer')}>Abrir video en YouTube</button>}
        <label className="mt-2 block text-sm">Reemplazar URL de video<input className="review-target mt-1 w-full rounded border p-2" value={sourceUrl} onChange={event => { setSourceUrl(event.target.value); setSourceError('') }} /></label>
        {sourceError && <p role="alert" className="mt-2 text-sm text-red-700">{sourceError}</p>}
        {saveSession.isError && <p role="alert" className="mt-2 text-sm text-red-700">No se pudo guardar la fuente: {message(saveSession.error)}</p>}
        <div className="mt-2 flex gap-2">
          <button className="btn" onClick={() => { player.retry(); sessionQuery.refetch(); setNotice('Se reintentó cargar la fuente.') }}>Reintentar</button>
          <button className="btn" disabled={saveSessionPending} onClick={() => { const url = sourceUrl.trim(); if (!supportedYouTubeUrl(url)) { setSourceError('Usá una URL válida de YouTube con un identificador de video.'); return } saveSession.mutate(replaceVideoSource(session, url)); setNotice('Fuente reemplazada. Esta fuente necesita un nuevo saque inicial para calibrar el reloj.') }}>Guardar reemplazo</button>
        </div>
        {manualPositionControl}
      </div></>
    )
  }
  return (
    <>
      {playerMount}
      <div className="mt-2 flex gap-2">
        <button className="btn" onClick={() => player.isPlaying ? player.pause() : player.play()}>{player.isPlaying ? 'Pausar' : 'Reproducir'}</button>
        <span className="self-center font-mono">Posición de video: {player.currentTime.toFixed(1)} s</span>
      </div>
      {manualPositionControl}
    </>
  )
}
