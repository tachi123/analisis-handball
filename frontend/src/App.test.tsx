import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from './hooks/useAuth'
import App from './App'

vi.mock('./pages/MatchReview', () => ({ default: () => <main>Protected review workspace</main> }))
vi.mock('./pages/MatchReportsTimeline', () => ({ default: () => <main>Protected reports timeline</main> }))
vi.mock('./pages/FixtureRosterPage', () => ({ default: () => <main>Protected fixture roster remediation</main> }))

describe('App review route', () => {
  afterEach(() => localStorage.clear())

  it('renders the protected review route for an authenticated analyst at runtime', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, email: 'analyst@example.com', full_name: 'Analyst', role: 'analyst', club_id: null, is_active: true, must_change_password: false }))

    render(<MemoryRouter initialEntries={['/match/42/review']}><AuthProvider><App /></AuthProvider></MemoryRouter>)

    expect(await screen.findByText('Protected review workspace')).toBeTruthy()
  })

  it('redirects an unauthenticated visitor from the protected review route', async () => {
    render(<MemoryRouter initialEntries={['/match/42/review']}><AuthProvider><App /></AuthProvider></MemoryRouter>)

    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeTruthy()
  })

  it('renders the protected timeline route for an authenticated analyst', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, email: 'analyst@example.com', full_name: 'Analyst', role: 'analyst', club_id: null, is_active: true, must_change_password: false }))
    render(<MemoryRouter initialEntries={['/match/42/timeline']}><AuthProvider><App /></AuthProvider></MemoryRouter>)
    expect(await screen.findByText('Protected reports timeline')).toBeTruthy()
  })

  it('redirects the protected reports compatibility route to the timeline at runtime', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, email: 'analyst@example.com', full_name: 'Analyst', role: 'analyst', club_id: null, is_active: true, must_change_password: false }))
    render(<MemoryRouter initialEntries={['/match/42/reports']}><AuthProvider><App /></AuthProvider></MemoryRouter>)

    expect(await screen.findByText('Protected reports timeline')).toBeTruthy()
  })

  it('redirects an unauthenticated visitor from the protected timeline route', async () => {
    render(<MemoryRouter initialEntries={['/match/42/timeline']}><AuthProvider><App /></AuthProvider></MemoryRouter>)
    expect(await screen.findByRole('button', { name: 'Ingresar' })).toBeTruthy()
  })

  it('renders roster remediation at the fixture-keyed protected route', async () => {
    localStorage.setItem('user', JSON.stringify({ id: 1, email: 'analyst@example.com', full_name: 'Analyst', role: 'analyst', club_id: null, is_active: true, must_change_password: false }))
    render(<MemoryRouter initialEntries={['/fixtures/fixture-1/roster']}><AuthProvider><App /></AuthProvider></MemoryRouter>)
    expect(await screen.findByText('Protected fixture roster remediation')).toBeTruthy()
  })
})
