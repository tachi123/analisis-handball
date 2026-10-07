import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import IncidentWizard from './IncidentWizard'

const players = {
  officialHomePlayers: [
    { key: 'home-10', jersey: 10, name: 'Local player', side: 'home' as const, playerId: 10 },
    { key: 'home-11', jersey: 11, name: 'Local substitute', side: 'home' as const, playerId: 11 },
  ],
  officialAwayPlayers: [{ key: 'away-20', jersey: 20, name: 'Away player', side: 'away' as const, playerId: 20 }],
}

it('uses the wizard-owned team selection for its visible selection and submitted command', () => {
  const onSubmit = vi.fn()
  render(<IncidentWizard
    isOpen
    onClose={vi.fn()}
    onSubmit={onSubmit}
    submitting={false}
    period={1}
    regulationSeconds={12}
    clockUnverified={false}
    teamId={null}
    homeTeam={{ id: 10, name: 'Local' }}
    awayTeam={{ id: 11, name: 'Visitante' }}
    {...players}
    hasVideo
    currentVideoTime={42}
    videoSourceId={4}
    videoUrl="https://youtu.be/abcdefghijk"
  />)

  fireEvent.click(screen.getByRole('button', { name: 'Local' }))
  expect(screen.queryByText('Seleccioná un equipo para continuar')).toBeNull()
  expect(screen.getByRole('button', { name: 'Local' }).className).toContain('btn-primary')
  fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))
  fireEvent.click(screen.getByRole('button', { name: 'GOL' }))
  fireEvent.click(screen.getByRole('button', { name: /registrar goal/i }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'shot', outcome: 'goal', team_id: 10 }))
})

it('marks the selected shot outcome and replaces it when another is chosen', () => {
  render(<IncidentWizard
    isOpen
    onClose={vi.fn()}
    onSubmit={vi.fn()}
    submitting={false}
    period={1}
    regulationSeconds={12}
    clockUnverified={false}
    teamId={10}
    homeTeam={{ id: 10, name: 'Local' }}
    awayTeam={{ id: 11, name: 'Visitante' }}
    {...players}
    hasVideo
    currentVideoTime={42}
    videoSourceId={4}
    videoUrl="https://youtu.be/abcdefghijk"
  />)

  fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))

  const goal = screen.getByRole('button', { name: 'GOL' })
  const save = screen.getByRole('button', { name: 'ATAJADA' })
  expect(goal.getAttribute('aria-pressed')).toBe('false')
  expect(save.getAttribute('aria-pressed')).toBe('false')

  fireEvent.click(goal)
  expect(goal.getAttribute('aria-pressed')).toBe('true')
  expect(goal.className).toContain('border-indigo-600')
  expect(save.getAttribute('aria-pressed')).toBe('false')

  fireEvent.click(save)
  expect(goal.getAttribute('aria-pressed')).toBe('false')
  expect(save.getAttribute('aria-pressed')).toBe('true')
  expect(save.className).toContain('border-indigo-600')
})

it('clears player selections when the team changes', () => {
  const onSubmit = vi.fn()
  render(<IncidentWizard isOpen onClose={vi.fn()} onSubmit={onSubmit} submitting={false} period={1}
    regulationSeconds={12} clockUnverified={false} teamId={10} homeTeam={{ id: 10, name: 'Local' }}
    awayTeam={{ id: 11, name: 'Visitante' }} {...players} hasVideo currentVideoTime={42}
    videoSourceId={4} videoUrl="https://youtu.be/abcdefghijk" />)

  fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))
  fireEvent.click(screen.getByRole('button', { name: 'GOL' }))
  fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: '10' } })
  fireEvent.click(screen.getByRole('button', { name: 'Visitante' }))
  fireEvent.click(screen.getByRole('button', { name: /registrar goal/i }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ team_id: 11, player_id: null, related_player_id: null }))
})

it('clears shot-only role IDs before submitting a non-shot event', () => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))
  fireEvent.click(screen.getByRole('button', { name: 'GOL' }))
  fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: '11' } })
  fireEvent.change(screen.getAllByRole('combobox')[2], { target: { value: '20' } })
  fireEvent.click(screen.getByRole('button', { name: 'Volver' }))
  fireEvent.click(screen.getByRole('button', { name: /cambio \/ tiempo/i }))
  fireEvent.click(screen.getByRole('button', { name: 'Time-out' }))
  fireEvent.click(screen.getByRole('button', { name: /registrar timeout/i }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'other', outcome: 'timeout', player_id: null, related_player_id: null, goalkeeper_id: null, shot_zone: null }))
  cleanup()
})

function renderWizard(onSubmit = vi.fn()) {
  render(<IncidentWizard isOpen onClose={vi.fn()} onSubmit={onSubmit} submitting={false} period={1}
    regulationSeconds={12} clockUnverified={false} teamId={10} homeTeam={{ id: 10, name: 'Local' }}
    awayTeam={{ id: 11, name: 'Visitante' }} {...players} hasVideo currentVideoTime={42}
    videoSourceId={4} videoUrl="https://youtu.be/abcdefghijk" />)
  return onSubmit
}

it.each([
  ['GOL', 'goal'], ['ATAJADA', 'save'], ['PALO', 'woodwork'], ['AFUERA', 'miss'], ['BLOQUEADO', 'blocked'],
])('submits the %s shot option as canonical %s', (label, outcome) => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))
  fireEvent.click(screen.getByRole('button', { name: label }))
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`registrar ${outcome.replace('_', ' ')}`, 'i') }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'shot', outcome }))
  cleanup()
})

it('records an optional opposing goalkeeper independently from the shooter and assistant', () => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /tiro al arco/i }))
  fireEvent.click(screen.getByRole('button', { name: 'GOL' }))
  fireEvent.change(screen.getAllByRole('combobox')[2], { target: { value: '20' } })
  fireEvent.click(screen.getByRole('button', { name: /registrar goal/i }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ player_id: null, related_player_id: null, goalkeeper_id: 20 }))
  cleanup()
})

it.each([
  ['2 minutos', 'two_minute_exclusion'], ['Amarilla', 'yellow_card'], ['Roja', 'red_card'],
  ['Azul', 'blue_card'], ['7 metros', 'seven_meter'],
])('submits the %s sanction option as canonical %s', (label, outcome) => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /falta \/ sanción/i }))
  fireEvent.click(screen.getByRole('button', { name: label }))
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`registrar ${outcome.replace('_', ' ')}`, 'i') }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'foul_sanction', outcome }))
  cleanup()
})

it.each([
  ['Arquero activo', 'active'], ['Arquero desconocido', 'unknown'],
])('submits the %s goalkeeper state as canonical %s', (label, outcome) => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /estado de arquero/i }))
  fireEvent.click(screen.getByRole('button', { name: label }))
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`registrar ${outcome}`, 'i') }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'goalkeeper_change', outcome }))
  cleanup()
})

it('submits the incoming player as active and the outgoing player as inactive', () => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /cambio \/ tiempo/i }))
  fireEvent.click(screen.getByRole('button', { name: 'Sustitución' }))
  fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: '10' } })
  fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: '11' } })
  fireEvent.click(screen.getByRole('button', { name: /registrar substitution/i }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
    kind: 'lineup_change', outcome: 'substitution', player_id: 11, related_player_id: 10,
  }))
})

it.each([
  ['Saque inicial / Inicio período', 'kickoff'], ['Fin de período', 'period_end'], ['Time-out', 'timeout'],
])('submits the %s team option as an other event', (label, outcome) => {
  const onSubmit = renderWizard()
  fireEvent.click(screen.getByRole('button', { name: /cambio \/ tiempo/i }))
  fireEvent.click(screen.getByRole('button', { name: label }))
  fireEvent.click(screen.getByRole('button', { name: new RegExp(`registrar ${outcome.replace('_', ' ')}`, 'i') }))

  expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ kind: 'other', outcome }))
  cleanup()
})
