import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MatchesPage from './MatchesPage'

const api = vi.hoisted(() => ({ createMatch: vi.fn(), getFixtures: vi.fn(), getMatches: vi.fn(), getTeams: vi.fn(), getTournaments: vi.fn() }))
vi.mock('../api/client', () => api)

const fixture = {
  fixture_key: 'fixture-1', stage: { name: 'Apertura' }, home_registration: { display_name: 'Ci.De.Co. B' }, away_registration: { display_name: 'S.A.P.A.' }, scheduled_date: '2026-04-12', roster_status: 'not_confirmed',
}
const manual = {
  id: 7, origin: 'manual', scheduled_match_id: null, home_team: { name: 'SAPA' }, away_team: { name: 'Banfield' }, date: '2026-04-12', tournament: null,
}

function renderPage() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><MatchesPage /></MemoryRouter></QueryClientProvider>)
}

describe('MatchesPage', () => {
  beforeEach(() => {
    api.getFixtures.mockResolvedValue([fixture])
    api.getMatches.mockResolvedValue([manual, { ...manual, id: 8, origin: 'fixture', scheduled_match_id: 3 }])
    api.getTeams.mockResolvedValue([{ id: 1, name: 'SAPA' }, { id: 2, name: 'Banfield' }])
    api.getTournaments.mockResolvedValue([])
    api.createMatch.mockResolvedValue(manual)
  })
  afterEach(() => { cleanup(); vi.clearAllMocks() })

  it('lists imported fixtures and manual records from the unified matches endpoint', async () => {
    renderPage()

    expect(await screen.findByText('Ci.De.Co. B vs S.A.P.A.')).toBeTruthy()
    expect(screen.getByText('SAPA vs Banfield')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Preparar planilla' }).getAttribute('href')).toBe('/matches/7/prepare')
    expect(api.getFixtures).toHaveBeenCalledWith('all')
    expect(api.getMatches).toHaveBeenCalledTimes(1)
  })

  it('creates a manual match through the current workflow', async () => {
    renderPage()
    await screen.findByText('Partidos manuales')
    fireEvent.click(screen.getByRole('button', { name: 'Crear partido manual' }))
    fireEvent.change(screen.getByLabelText('Equipo local'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Equipo visitante'), { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear y cargar planilla' }))

    await waitFor(() => expect(api.createMatch).toHaveBeenCalledWith(expect.objectContaining({
      home_team_id: 1, away_team_id: 2, tournament_id: null, date: null, match_time: null,
    })))
  })
})
