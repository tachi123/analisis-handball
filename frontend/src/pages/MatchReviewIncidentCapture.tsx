interface IncidentCaptureProps {
  matchQuery: any
  teamId: number | null
  setTeamId: (v: number | null) => void
  hasValidClockStart: boolean
  pendingKickoff: any | null
  pendingKickoffs: any[]
  selectPendingKickoff: (eventId: number) => void
  videoReady: boolean
  mark: any
  recordKickoff: () => void
  recordingKickoff: boolean
  calibrateKickoff: () => void
  calibratingKickoff: boolean
  setWizardOpen: (v: boolean) => void
  wizardOpen: boolean
  profileLabel: string
  canMark: boolean
}

export function IncidentCapture({ matchQuery, teamId, setTeamId, hasValidClockStart: _hasValidClockStart, pendingKickoff, pendingKickoffs, selectPendingKickoff, videoReady, mark, recordKickoff, recordingKickoff, calibrateKickoff, calibratingKickoff, setWizardOpen, wizardOpen: _wizardOpen, profileLabel: _profileLabel, canMark }: IncidentCaptureProps) {
  const homeTeam = matchQuery.data.home_team
  const awayTeam = matchQuery.data.away_team
  const validTeams = [homeTeam?.id, awayTeam?.id].filter((id): id is number => typeof id === 'number' && id > 0)
  const selectedTeamName = teamId === homeTeam?.id ? homeTeam?.name : teamId === awayTeam?.id ? awayTeam?.name : null
  const missingTeams = validTeams.length !== 2

  return (
    <section className="card space-y-3" aria-labelledby="capture-heading">
      <div className="flex items-center justify-between">
        <h2 id="capture-heading" className="font-semibold">Registrar incidente</h2>
        {canMark && <button className="btn btn-primary min-h-11" onClick={() => setWizardOpen(true)} disabled={mark.isPending}>
          {mark.isPending ? 'Registrando…' : 'Nuevo incidente (+)' }
        </button>}
      </div>
       {!canMark && !pendingKickoff && pendingKickoffs.length === 0 && <div className="rounded bg-amber-50 p-3 text-sm text-amber-900"><p>Primero ubicá el video en el saque inicial. Podés reproducirlo o pausarlo manualmente antes de registrar la posesión inicial.</p>{missingTeams ? <p role="alert" className="mt-2">Faltan las identidades Local y Visitante del partido. Completalas antes de registrar el saque inicial.</p> : <><div className="mt-2 flex flex-wrap gap-2"><button className={`btn ${teamId === homeTeam?.id ? 'btn-primary' : ''}`} onClick={() => setTeamId(homeTeam.id)}>{homeTeam.name}</button><button className={`btn ${teamId === awayTeam?.id ? 'btn-primary' : ''}`} onClick={() => setTeamId(awayTeam.id)}>{awayTeam.name}</button></div>{selectedTeamName && <p className="mt-2">Posesión inicial seleccionada: <strong>{selectedTeamName}</strong>.</p>}</>}<button className="btn btn-primary mt-2" disabled={missingTeams || !videoReady || teamId === null || !validTeams.includes(teamId) || recordingKickoff} onClick={recordKickoff}>{recordingKickoff ? 'Registrando saque inicial…' : 'Registrar saque inicial y posesión'}</button>{!videoReady && <p className="mt-2">Esperá a que el reproductor esté listo para capturar evidencia de video.</p>}</div>}
       {!canMark && !pendingKickoff && pendingKickoffs.length > 1 && <div className="rounded bg-amber-50 p-3 text-sm text-amber-900"><p>Hay varios saques iniciales pendientes para este período. Elegí explícitamente cuál corresponde al video antes de calibrar.</p><div className="mt-2 flex flex-wrap gap-2">{pendingKickoffs.map(event => <button key={event.id} className="btn" onClick={() => selectPendingKickoff(event.id)}>Usar saque #{event.id}</button>)}</div></div>}
      {pendingKickoff && <div className="rounded bg-amber-50 p-3 text-sm text-amber-900"><p>Se registró el saque inicial y la posesión de {pendingKickoff.payload.team_id === homeTeam?.id ? homeTeam?.name : awayTeam?.name}. Ahora calibrá su ancla de video como reloj oficial.</p><button className="btn btn-primary mt-2" disabled={calibratingKickoff} onClick={calibrateKickoff}>{calibratingKickoff ? 'Calibrando…' : 'Declarar este saque inicial como 00:00'}</button></div>}
       {canMark && <p className="text-sm text-gray-600">Cada acción crea un hecho canónico con el reloj de partido derivado del video. Elegí equipo y luego el tipo de incidente.</p>}
      {mark.isError && <p role="alert" className="text-red-700">No se pudo marcar: {message(mark.error)}</p>}
    </section>
  )
}

const message = (error: unknown) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : error instanceof Error ? error.message : 'Error de red o validación'
}
