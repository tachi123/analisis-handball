import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ReportEventTimeline from './ReportEventTimeline'
import { emptyReportFilters, sortTimelineEvents } from '../reportTimeline'
import type { CanonicalEvent } from '../types'

const events: CanonicalEvent[] = [
  { id: 1, sequence: 1, active: true, revision: 2, reason: 'verified', payload: { kind: 'shot', period: 1, regulation_seconds: 30, clock_unverified: true, team_id: null, player_id: 7, outcome: 'goal', fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null, roster_source: 'match_squad' }, evidence: [{ id: 1, kind: 'video', video_anchor_seconds: 10, uncertainty: [] }] },
  { id: 2, sequence: 2, active: false, payload: { kind: 'turnover', period: 2, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, outcome: null, fact_kind: 'observed', evidence_state: 'ambiguous', uncertainty: [], note: null }, evidence: [] },
]

describe('ReportEventTimeline', () => {
  it('announces filters, exposes uncertainty, selection detail, and scoped keyboard navigation', () => {
    const onSelect = vi.fn(); const onFiltersChange = vi.fn()
    render(<ReportEventTimeline rows={sortTimelineEvents(events)} filters={emptyReportFilters} allEvents={events} selected={null} playerLabels={{ 7: '#7 Ana' }} notice="" onSelect={onSelect} onFiltersChange={onFiltersChange} />)
    expect(screen.getByRole('status').textContent).toContain('2 eventos visibles')
    expect(screen.getAllByText(/tiempo de partido pendiente de confirmar/i).length).toBeGreaterThan(0)
    fireEvent.change(screen.getByLabelText('Filtrar por jugador'), { target: { value: '7' } })
    expect(onFiltersChange).toHaveBeenCalledWith(expect.objectContaining({ playerId: 7 }))
    const first = screen.getByRole('button', { name: /#1/ })
    fireEvent.keyDown(first, { key: 'ArrowDown' })
    expect(onSelect).toHaveBeenCalledWith(events[1])
    fireEvent.keyDown(screen.getByRole('button', { name: /#2/ }), { key: 'Home' })
    expect(onSelect).toHaveBeenCalledWith(events[0])
    fireEvent.keyDown(first, { key: 'End' })
    expect(onSelect).toHaveBeenCalledWith(events[1])
    fireEvent.keyDown(screen.getByLabelText('Filtrar por tipo'), { key: 't' })
    expect(onSelect).not.toHaveBeenCalledTimes(4)
    fireEvent.click(first)
    expect(onSelect).toHaveBeenCalledWith(events[0])
  })

  it('renders the complete current canonical detail and no mutation or history controls', () => {
    render(<ReportEventTimeline rows={sortTimelineEvents(events)} filters={emptyReportFilters} allEvents={events} selected={events[0]} playerLabels={{ 7: '#7 Ana' }} notice="Evento seleccionado" onSelect={vi.fn()} onFiltersChange={vi.fn()} />)
    const detail = screen.getByLabelText('Detalle del evento')
    expect(detail.textContent).toContain('Evidencia actual')
    expect(detail.textContent).toContain('Video · video 10.0 s')
    expect(detail.textContent).toContain('Lanzamiento')
    expect(detail.textContent).toContain('Confirmada')
    expect(detail.textContent).toContain('Tiempo de partido pendiente de confirmar')
    expect(screen.queryByRole('button', { name: /revisar|guardar|excluir/i })).toBeNull()
  })
})
