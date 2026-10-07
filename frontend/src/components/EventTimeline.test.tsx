import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EventTimeline, { closestEventId } from './EventTimeline'
import type { CanonicalEvent } from '../types'

const events: CanonicalEvent[] = [
  { id: 1, sequence: 1, active: true, payload: { kind: 'shot', period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, outcome: 'goal', fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null }, evidence: [{ id: 1, kind: 'video', reference: 'https://youtube.test', video_source_id: 2, video_anchor_seconds: 12, uncertainty: [] }] },
  { id: 2, sequence: 2, active: true, payload: { kind: 'turnover', period: 1, regulation_seconds: null, clock_unverified: false, team_id: null, player_id: null, outcome: null, fact_kind: 'observed', evidence_state: 'no_visible', uncertainty: [], note: null }, evidence: [], },
]

describe('EventTimeline', () => {
  it('selects anchored events and clearly explains no-seek events', () => {
    const onSelect = vi.fn(); const onViewVideo = vi.fn(); const onRevise = vi.fn()
    render(<EventTimeline events={events} selectedId={null} highlightedId={null} onSelect={onSelect} onViewVideo={onViewVideo} onRevise={onRevise} />)
    fireEvent.click(screen.getByRole('button', { name: /#1/ }))
    expect(onSelect).toHaveBeenCalledWith(events[0])
    expect(screen.getAllByRole('button', { name: /tiempo de partido pendiente de confirmar/i }).length).toBeGreaterThan(0)
    expect(screen.getByText(/Lanzamiento/)).toBeTruthy()
    expect(screen.getByText(/evidencia de video no disponible/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Ver en video' }))
    expect(onViewVideo).toHaveBeenCalledWith(events[0])
  })

  it('finds the closest event that actually has video evidence', () => {
    expect(closestEventId(events, 10)).toBe(1)
    expect(closestEventId([events[1]], 10)).toBeNull()
  })

  it('auto-scrolls the runtime-highlighted row and gives revise controls a 44px target', () => {
    const scrollIntoView = vi.fn()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: scrollIntoView })
    render(<EventTimeline events={events} selectedId={null} highlightedId={1} onSelect={vi.fn()} onRevise={vi.fn()} />)

    expect(screen.getByRole('button', { name: /#1/ }).getAttribute('aria-current')).toBe('true')
    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' })
    expect(screen.getAllByRole('button', { name: /editar incidencia/i })[0].className).toContain('review-target')
  })

  it('shows available shooter and opposing goalkeeper attribution', () => {
    const shot = { ...events[0], payload: { ...events[0].payload, team_id: 1, player_id: 10, goalkeeper_id: 20 } }
    render(<EventTimeline events={[shot]} selectedId={null} highlightedId={null} onSelect={vi.fn()} onRevise={vi.fn()} playerLabels={{ 10: 'Tiradora', 20: 'Arquera rival' }} />)
    expect(screen.getByText(/Tirador: Tiradora/)).toBeTruthy()
    expect(screen.getByText(/Arquero rival: Arquera rival/)).toBeTruthy()
  })
})
