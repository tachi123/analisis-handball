import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CanonicalEvent } from '../types'

const { createCanonicalEvent, deactivateLastCanonicalEvent, enableCanonicalAnalysis, getAnalysisSession, getCanonicalEvents, getMatch, getOfficialSheet, reviseCanonicalEvent, saveAnalysisSession, playerState } = vi.hoisted(() => ({
  createCanonicalEvent: vi.fn(), deactivateLastCanonicalEvent: vi.fn(), enableCanonicalAnalysis: vi.fn(), getAnalysisSession: vi.fn(), getCanonicalEvents: vi.fn(), getMatch: vi.fn(), getOfficialSheet: vi.fn(), reviseCanonicalEvent: vi.fn(), saveAnalysisSession: vi.fn(), playerState: { currentTime: 50, freshTime: 50, availability: 'ready' as 'ready' | 'player_error', retry: vi.fn(), seekTo: vi.fn(), pause: vi.fn(), setCurrentTimeManual: vi.fn() },
}))
vi.mock('../api/client', () => ({
  getMatch,
  getOfficialSheet,
  getAnalysisSession, getCanonicalEvents, saveAnalysisSession, createCanonicalEvent,
  reviseCanonicalEvent, enableCanonicalAnalysis, deactivateCanonicalEvent: vi.fn(), deactivateLastCanonicalEvent, resetCanonicalAnalysis: vi.fn(),
}))
vi.mock('../hooks/useYouTubeSync', () => ({ useYouTubeSync: () => ({ playerRef: { current: null }, currentTime: playerState.currentTime, isPlaying: false, availability: playerState.availability, seekTo: playerState.seekTo, play: vi.fn(), pause: playerState.pause, retry: playerState.retry, pauseAndReadCurrentTime: vi.fn(async () => playerState.freshTime), setCurrentTimeManual: playerState.setCurrentTimeManual }) }))
import MatchReview from './MatchReview'

const event: CanonicalEvent = { id: 7, sequence: 1, active: true, payload: { kind: 'other', period: 1, regulation_seconds: 0, clock_unverified: false, team_id: 10, player_id: null, related_player_id: null, outcome: 'kickoff', fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null }, evidence: [{ id: 1, kind: 'video', reference: 'https://youtu.be/abcdefghijk', video_source_id: 4, video_anchor_seconds: 50, uncertainty: [] }] }
const pendingKickoff: CanonicalEvent = { ...event, payload: { ...event.payload, regulation_seconds: null, clock_unverified: true }, evidence: [{ ...event.evidence![0], video_anchor_seconds: 17 }] }
const session = (profile: 'complete' | 'classic' | 'goalkeepers' = 'complete', clockStart: number | null = 0) => ({ id: 2, match_id: 1, analyst_id: 1, mode: 'video' as const, profile, source: { id: 4, original_url: 'https://youtu.be/abcdefghijk', provider: 'youtube', provider_video_id: 'abcdefghijk', availability_state: 'ready' as const }, video_position_seconds: 50, clock_start_video_seconds: clockStart, angle: null, filters: {}, draft: {}, queue: [], anchors: [], time_segments: [] })
const renderWorkspace = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/match/1/review']}><Routes><Route path="/match/:matchId/review" element={<MatchReview />} /></Routes></MemoryRouter></QueryClientProvider>)

describe('MatchReview', () => {
  beforeEach(() => { vi.clearAllMocks(); playerState.currentTime = 50; playerState.freshTime = 50; playerState.availability = 'ready'; getMatch.mockResolvedValue({ id: 1, canonical_analysis_enabled: true, home_team: { id: 10, name: 'Local' }, away_team: { id: 11, name: 'Visitante' } }); getOfficialSheet.mockResolvedValue({ home: { name: 'Local', score: 20, players: [] }, away: { name: 'Visitante', score: 19, players: [] }, provenance: { filename: 'official.pdf' } }); getCanonicalEvents.mockResolvedValue([event]); getAnalysisSession.mockResolvedValue(session()); createCanonicalEvent.mockResolvedValue(event); reviseCanonicalEvent.mockResolvedValue(event); saveAnalysisSession.mockResolvedValue(session()); enableCanonicalAnalysis.mockResolvedValue({ canonical_analysis_enabled: true }); deactivateLastCanonicalEvent.mockResolvedValue(event) })

  it('derives the game clock immediately from the reloaded kickoff calibration and player position', async () => {
    getAnalysisSession.mockResolvedValue(session('complete', 17))
    renderWorkspace()
    expect(await screen.findByText('00:33')).toBeTruthy()
    expect(screen.getAllByText('Posición de video: 50.0 s')).toHaveLength(2)
  })

  it('keeps a calibrated kickoff recognized after an ordinary session save and reload', async () => {
    playerState.availability = 'player_error'
    const unavailableSession = { ...session('complete', 17), source: { ...session().source, availability_state: 'player_error' as const } }
    getAnalysisSession.mockResolvedValue(unavailableSession)
    saveAnalysisSession.mockResolvedValue({ ...unavailableSession, video_position_seconds: 83 })
    renderWorkspace()

    expect(await screen.findByText('00:33')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Ajustar posición de video' }))
    fireEvent.change(screen.getByLabelText(/posición de video \(mm:ss o segundos\)/i), { target: { value: '83' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar posición de video' }))

    await waitFor(() => expect(saveAnalysisSession).toHaveBeenCalledWith(1, expect.objectContaining({ video_position_seconds: 83 })))
    expect(await screen.findByText('00:33')).toBeTruthy()
    expect(screen.getByRole('button', { name: /nuevo incidente/i })).toBeTruthy()
  })

  it('does not recover a calibrated kickoff from another video source', async () => {
    getAnalysisSession.mockResolvedValue({ ...session('complete', 17), source: { ...session().source, id: 5, original_url: 'https://youtu.be/zyxwvutsrq', provider_video_id: 'zyxwvutsrq' } })
    renderWorkspace()

    expect(await screen.findByText('Inicio del partido pendiente de confirmar')).toBeTruthy()
    expect(screen.queryByText('00:33')).toBeNull()
    expect(screen.queryByRole('button', { name: /nuevo incidente/i })).toBeNull()
  })

  it('parses and persists an explicit manual video position when YouTube is unavailable', async () => {
    playerState.availability = 'player_error'
    getAnalysisSession.mockResolvedValue(session('complete', 17))
    saveAnalysisSession.mockResolvedValue({ ...session('complete', 17), source: { ...session().source, availability_state: 'player_error' as const }, video_position_seconds: 83 })
    renderWorkspace()
    fireEvent.click(await screen.findByRole('button', { name: 'Ajustar posición de video' }))
    fireEvent.change(screen.getByLabelText(/posición de video \(mm:ss o segundos\)/i), { target: { value: '01:23' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar posición de video' }))
    await waitFor(() => expect(playerState.setCurrentTimeManual).toHaveBeenCalledWith(83))
    expect(saveAnalysisSession).toHaveBeenCalledWith(1, expect.objectContaining({ video_position_seconds: 83 }))
    expect(await screen.findByRole('button', { name: /nuevo incidente/i })).toBeTruthy()
  })

  it('seeks and pauses at an event evidence timestamp from the visible video action', async () => {
    renderWorkspace()
    fireEvent.click(await screen.findByRole('button', { name: 'Ver en video' }))
    expect(playerState.pause).toHaveBeenCalledOnce()
    expect(playerState.seekTo).toHaveBeenCalledWith(50)
  })

  it('shows a confirmed-sheet start action instead of querying a disabled canonical workspace', async () => {
    getMatch.mockResolvedValue({ id: 1, canonical_analysis_enabled: false, home_team: { id: 10, name: 'Local' }, away_team: { id: 11, name: 'Visitante' } })
    renderWorkspace()
    fireEvent.click(await screen.findByRole('button', { name: 'Iniciar análisis' }))
    await waitFor(() => expect(enableCanonicalAnalysis).toHaveBeenCalledWith(1))
    expect(getCanonicalEvents).not.toHaveBeenCalled()
  })

  it('keeps a disabled match read-only when its official sheet is unavailable', async () => {
    getMatch.mockResolvedValue({ id: 1, canonical_analysis_enabled: false, home_team: { id: 10, name: 'Local' }, away_team: { id: 11, name: 'Visitante' } })
    getOfficialSheet.mockRejectedValue({ response: { status: 404 } })
    renderWorkspace()
    expect(await screen.findByText(/solo lectura hasta que se confirme la planilla oficial/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Iniciar análisis' })).toBeNull()
    expect(getCanonicalEvents).not.toHaveBeenCalled()
  })

  it('shows an official-sheet error and retries instead of treating an unknown failure as an unconfirmed sheet', async () => {
    getMatch.mockResolvedValue({ id: 1, canonical_analysis_enabled: false, home_team: { id: 10, name: 'Local' }, away_team: { id: 11, name: 'Visitante' } })
    getOfficialSheet.mockRejectedValueOnce(new Error('Sin conexión')).mockResolvedValueOnce({ home: { name: 'Local', score: 20, players: [] }, away: { name: 'Visitante', score: 19, players: [] }, provenance: { filename: 'official.pdf' } })
    renderWorkspace()

    expect(await screen.findByText(/no se pudo verificar la planilla oficial/i)).toBeTruthy()
    expect(screen.queryByText(/solo lectura hasta que se confirme/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /reintentar verificar planilla/i }))
    expect(await screen.findByRole('button', { name: 'Iniciar análisis' })).toBeTruthy()
  })

  it('keeps canonical actions available when the official-sheet status is temporarily unknown', async () => {
    getOfficialSheet.mockRejectedValue(new Error('Sin conexión'))
    renderWorkspace()

    expect(await screen.findByText(/no se pudo cargar la planilla oficial/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: /nuevo incidente/i })).toBeTruthy()
  })

  it('shows an event loading error instead of the empty timeline and retries the query', async () => {
    getCanonicalEvents.mockRejectedValueOnce(new Error('Sin conexión')).mockResolvedValueOnce([])
    renderWorkspace()

    expect(await screen.findByText(/no se pudieron cargar los eventos canónicos/i)).toBeTruthy()
    expect(screen.queryByText('Todavía no hay eventos canónicos.')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /reintentar cargar eventos/i }))
    expect(await screen.findByText('Todavía no hay eventos canónicos.')).toBeTruthy()
  })

  it('disables deletion of another analyst’s last active event', async () => {
    getCanonicalEvents.mockResolvedValue([{ ...event, actor_id: 2 }])
    renderWorkspace()

    const deleteLast = await screen.findByRole('button', { name: 'Eliminar última incidencia' }) as HTMLButtonElement
    expect(deleteLast.disabled).toBe(true)
    expect(screen.getByText(/fue registrada por otra persona/i)).toBeTruthy()
  })

  it('invalidates canonical events after deleting the current analyst’s last event', async () => {
    getCanonicalEvents.mockResolvedValue([{ ...event, actor_id: 1 }])
    renderWorkspace()

    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar última incidencia' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    await waitFor(() => expect(deactivateLastCanonicalEvent).toHaveBeenCalledWith(1, 'Eliminación de la última incidencia por el analista'))
    await waitFor(() => expect(getCanonicalEvents).toHaveBeenCalledTimes(2))
  })

  it('records the selected pre-match possession as an unverified canonical kickoff with video evidence', async () => {
    getAnalysisSession.mockResolvedValue(session('complete', null))
    getCanonicalEvents.mockResolvedValue([])
    renderWorkspace()
    await screen.findByRole('button', { name: /registrar saque inicial y posesión/i })
    const playerMount = screen.getByTitle('Video del partido')
    expect(screen.queryByRole('button', { name: /nuevo incidente/i })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Local' }))
    expect(screen.getByText(/posesión inicial seleccionada:/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /registrar saque inicial y posesión/i }))
    await waitFor(() => expect(createCanonicalEvent).toHaveBeenCalledWith(1, expect.objectContaining({ kind: 'other', outcome: 'kickoff', team_id: 10, regulation_seconds: null, clock_unverified: true, evidence: [{ kind: 'video', reference: 'https://youtu.be/abcdefghijk', video_source_id: 4, video_anchor_seconds: 50, uncertainty: [] }] })))
    expect(screen.getByTitle('Video del partido')).toBe(playerMount)
  })

  it('recovers a pending kickoff and calibrates its stored anchor rather than the current player time', async () => {
    playerState.currentTime = 50
    getAnalysisSession.mockResolvedValueOnce(session('complete', null)).mockResolvedValue(session('complete', 17))
    getCanonicalEvents.mockResolvedValueOnce([pendingKickoff]).mockResolvedValue([event])
    saveAnalysisSession.mockResolvedValueOnce(session('complete', 17))
    reviseCanonicalEvent.mockResolvedValueOnce(event)
    renderWorkspace()

    await screen.findByRole('button', { name: /declarar este saque inicial como 00:00/i })
    expect(screen.queryByRole('button', { name: /nuevo incidente/i })).toBeNull()
    expect(screen.getByRole('button', { name: /declarar este saque inicial como 00:00/i })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /declarar este saque inicial como 00:00/i }))
    await waitFor(() => expect(saveAnalysisSession).toHaveBeenCalledWith(1, expect.objectContaining({ clock_start_video_seconds: 17 })))
    await waitFor(() => expect(reviseCanonicalEvent).toHaveBeenCalledWith(7, expect.objectContaining({ regulation_seconds: 0, clock_unverified: false, reason: expect.stringMatching(/calibración/i) })))
    await waitFor(() => expect(getAnalysisSession).toHaveBeenCalledTimes(2))
    await screen.findByRole('button', { name: /nuevo incidente/i })
  })

  it('does not offer a pending kickoff from another video source for calibration', async () => {
    getAnalysisSession.mockResolvedValue({ ...session('complete', null), source: { ...session().source, id: 5, original_url: 'https://youtu.be/zyxwvutsrq', provider_video_id: 'zyxwvutsrq' } })
    getCanonicalEvents.mockResolvedValue([pendingKickoff])
    renderWorkspace()

    expect(await screen.findByText(/esta fuente de video necesita un saque inicial calibrado/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /declarar este saque inicial como 00:00/i })).toBeNull()
  })

  it('clears source-bound calibration when replacing the session video source', async () => {
    playerState.availability = 'player_error'
    getAnalysisSession.mockResolvedValue({ ...session('complete', 17), anchors: [{ id: 1, period: 1, video_seconds: 17, regulation_seconds: 0, uncertainty_seconds: 0 }], time_segments: [{ id: 1, period: 1, video_start_seconds: 17, video_end_seconds: 50, regulation_start_seconds: 0, regulation_end_seconds: 33, uncertainty_seconds: 0, coverage: 'play', clock_unverified: false }] })
    renderWorkspace()

    fireEvent.change(await screen.findByLabelText(/reemplazar url de video/i), { target: { value: 'https://youtu.be/zyxwvutsrq' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar reemplazo' }))

    await waitFor(() => expect(saveAnalysisSession).toHaveBeenCalledWith(1, expect.objectContaining({ source: { url: 'https://youtu.be/zyxwvutsrq', availability_state: 'unknown' }, video_position_seconds: null, clock_start_video_seconds: null, anchors: [], time_segments: [] })))
  })

  it('requires an explicit kickoff selection when the active period has multiple pending kickoffs', async () => {
    getAnalysisSession.mockResolvedValue(session('complete', null))
    getCanonicalEvents.mockResolvedValue([pendingKickoff, { ...pendingKickoff, id: 8, evidence: [{ ...pendingKickoff.evidence![0], video_anchor_seconds: 23 }] }])
    renderWorkspace()

    expect(await screen.findByText(/varios saques iniciales pendientes/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /declarar este saque inicial como 00:00/i })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Usar saque #8' }))
    fireEvent.click(await screen.findByRole('button', { name: /declarar este saque inicial como 00:00/i }))
    await waitFor(() => expect(saveAnalysisSession).toHaveBeenCalledWith(1, expect.objectContaining({ clock_start_video_seconds: 23 })))
  })

  it('uses a canonical shot command rather than relabelling other and keeps official context visible', async () => {
    getAnalysisSession.mockResolvedValue(session('complete', 0.1))
    renderWorkspace()
    await screen.findByText('Contexto oficial')
    fireEvent.click(screen.getByRole('button', { name: /nuevo incidente/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Local' }))
    fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))
    fireEvent.click(screen.getByRole('button', { name: 'GOL' }))
    fireEvent.click(screen.getByRole('button', { name: /registrar goal/i }))
    await waitFor(() => expect(createCanonicalEvent).toHaveBeenCalledWith(1, expect.objectContaining({ kind: 'shot', outcome: 'goal', team_id: 10, regulation_seconds: 50, clock_unverified: false })))
  })

  it('supplies actual teams and official players when editing a reviewed shot', async () => {
    const shot = { ...event, payload: { ...event.payload, kind: 'shot' as const, player_id: 10, goalkeeper_id: 20, outcome: 'goal' } }
    getCanonicalEvents.mockResolvedValue([shot])
    getOfficialSheet.mockResolvedValue({
      home: { name: 'Local', score: 20, players: [{ jersey_number: 10, name: 'Tiradora', player_id: 10 }] },
      away: { name: 'Visitante', score: 19, players: [{ jersey_number: 1, name: 'Arquera', player_id: 20 }] },
      provenance: { filename: 'official.pdf' },
    })
    renderWorkspace()

    fireEvent.click(await screen.findByRole('button', { name: 'Editar incidencia' }))
    expect(screen.getByLabelText('Equipo').textContent).toContain('Local')
    expect(screen.getByLabelText('Tirador').textContent).toContain('Tiradora')
    expect(screen.getByLabelText('Arquero rival (opcional)').textContent).toContain('Arquera')
    fireEvent.click(screen.getByRole('button', { name: /guardar edición/i }))
    await waitFor(() => expect(reviseCanonicalEvent).toHaveBeenCalledWith(7, expect.objectContaining({ team_id: 10, player_id: 10, goalkeeper_id: 20 })))
  })

  it('exposes profile-appropriate goalkeeper controls and makes calibration optional', async () => {
    getAnalysisSession.mockResolvedValue(session('goalkeepers', 0.1))
    renderWorkspace()
    expect(await screen.findByText('Perfil: Arqueros')).toBeTruthy()
    expect(screen.getByRole('button', { name: /nuevo incidente/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /mostrar calibración avanzada/i })).toBeTruthy()
    expect(screen.getByText(/el comienzo del reloj alcanza/i)).toBeTruthy()
  })

  it('keeps the player mount available and retries the player from the unavailable UI', async () => {
    playerState.availability = 'player_error'
    renderWorkspace()

    await screen.findByRole('alert')
    const playerMount = screen.getByTitle('Video del partido')
    expect(playerMount.classList.contains('aspect-video')).toBe(true)
    expect(playerMount.classList.contains('w-full')).toBe(true)
    expect(playerMount.classList.contains('hidden')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() => expect(playerState.retry).toHaveBeenCalledOnce())
    expect(screen.getByTitle('Video del partido')).toBe(playerMount)
  })

  it('disables kickoff with actionable copy when either match team is missing', async () => {
    getAnalysisSession.mockResolvedValue(session('complete', null))
    getCanonicalEvents.mockResolvedValue([])
    getMatch.mockResolvedValue({ id: 1, canonical_analysis_enabled: true, home_team: { id: 10, name: 'Local' }, away_team: null })
    renderWorkspace()
    const kickoff = await screen.findByRole('button', { name: /registrar saque inicial y posesión/i }) as HTMLButtonElement
    expect(kickoff.disabled).toBe(true)
    expect(screen.getByText(/faltan las identidades local y visitante/i)).toBeTruthy()
  })
})
