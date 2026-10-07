import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EvidenceModal from './EvidenceModal'
import type { CanonicalEvent } from '../types'

const event: CanonicalEvent = { id: 1, sequence: 3, active: true, payload: { kind: 'other', period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, related_player_id: null, outcome: null, fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null } }

describe('EvidenceModal scenarios', () => {
  it('shows clock_unverified alongside a revisable event and persists playable provenance', () => {
    const onSave = vi.fn()
    render(<EvidenceModal event={event} source={{ id: 9, original_url: 'https://youtube.com/watch?v=abcdefghijk', provider: 'youtube', provider_video_id: 'abcdefghijk', availability_state: 'ready' }} currentTime={42} playable clockUnverified onSave={onSave} onClose={vi.fn()} />)

    expect(screen.getByText(/tiempo de partido pendiente de confirmar/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /guardar edición/i }))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ reason: 'Revisión de video', evidence: [{ kind: 'unavailable', uncertainty: ['not_visible'] }] }))
  })

  it('keeps no-playback evidence analyzable without a video anchor', () => {
    const onSave = vi.fn()
    const modal = render(<EvidenceModal event={event} source={null} currentTime={42} playable={false} clockUnverified={false} onSave={onSave} onClose={vi.fn()} />)

    fireEvent.click(modal.getByLabelText('ambiguous'))
    fireEvent.click(modal.getByRole('button', { name: /guardar edición/i }))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ evidence_state: 'ambiguous', evidence: [{ kind: 'unavailable', uncertainty: ['ambiguous_video'] }] }))
  })

  it('retains a selected IHF zone when revising a shot', () => {
    const onSave = vi.fn()
    const shot = { ...event, payload: { ...event.payload, kind: 'shot' as const, outcome: 'goal', shot_zone: 4 as const } }
    render(<EvidenceModal event={shot} source={null} currentTime={42} playable={false} clockUnverified={false} onSave={onSave} onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Zona IHF 4' }).getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(screen.getByRole('button', { name: /guardar edición/i }))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ shot_zone: 4 }))
  })

  it('preserves fixture, PDF, and historical video evidence while updating the current video anchor', () => {
    const onSave = vi.fn()
    const shot = { ...event, payload: { ...event.payload, kind: 'shot' as const, team_id: 1, player_id: 10, outcome: 'goal', note: 'Original', goalkeeper_id: null } }
    const evidence = [
      { id: 1, kind: 'fixture' as const, reference: 'fixture', scheduled_match_id: 3, uncertainty: [] },
      { id: 2, kind: 'pdf' as const, reference: 'sheet.pdf', official_snapshot_id: 'pdf-1', uncertainty: [] },
      { id: 3, kind: 'video' as const, reference: 'https://youtu.be/history', video_source_id: 8, video_anchor_seconds: 20, uncertainty: [] },
      { id: 4, kind: 'video' as const, reference: 'https://youtube.com/watch?v=abcdefghijk', video_source_id: 9, video_anchor_seconds: 42, uncertainty: [] },
    ]
    render(<EvidenceModal event={{ ...shot, evidence }} source={{ id: 9, original_url: 'https://youtube.com/watch?v=abcdefghijk', provider: 'youtube', provider_video_id: 'abcdefghijk', availability_state: 'ready' }} currentTime={42} playable clockUnverified={false} teams={{ home: { id: 1, name: 'Local' }, away: { id: 2, name: 'Visitante' } }} players={[{ key: 'home', jersey: 10, name: 'Tirador', side: 'home', playerId: 10 }, { key: 'away', jersey: 1, name: 'Arquero', side: 'away', playerId: 20 }]} onSave={onSave} onClose={vi.fn()} />)

    expect((screen.getByLabelText('Resultado') as HTMLInputElement).value).toBe('goal')
    expect((screen.getByLabelText('Notas') as HTMLTextAreaElement).value).toBe('Original')
    fireEvent.change(screen.getByLabelText('Arquero rival (opcional)'), { target: { value: '20' } })
    fireEvent.change(screen.getByLabelText('Marca de video (segundos, opcional)'), { target: { value: '43.5' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar edición/i }))
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ player_id: 10, goalkeeper_id: 20, evidence: expect.arrayContaining([
      expect.objectContaining({ kind: 'fixture', scheduled_match_id: 3 }),
      expect.objectContaining({ kind: 'pdf', official_snapshot_id: 'pdf-1' }),
      expect.objectContaining({ video_source_id: 8, video_anchor_seconds: 20 }),
      expect.objectContaining({ video_source_id: 9, video_anchor_seconds: 43.5 }),
    ]) }))
  })

  it('gives close, text, and radio-label controls a 44px review target', () => {
    render(<EvidenceModal event={event} source={null} currentTime={42} playable={false} clockUnverified={false} onSave={vi.fn()} onClose={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Cerrar' }).className).toContain('review-target')
    expect(screen.getByLabelText('Motivo de revisión').className).toContain('review-target')
    expect(screen.getByText('confirmed').closest('label')?.className).toContain('review-target')
  })

  it('closes on Escape and retains the edited draft after a relevant API error', () => {
    const onClose = vi.fn()
    const view = render(<EvidenceModal event={event} source={null} currentTime={42} playable={false} clockUnverified={false} onSave={vi.fn()} onClose={onClose} />)

    fireEvent.change(screen.getByLabelText('Motivo de revisión'), { target: { value: 'Retener este motivo' } })
    view.rerender(<EvidenceModal event={event} source={null} currentTime={42} playable={false} clockUnverified={false} error="403 Forbidden" onSave={vi.fn()} onClose={onClose} />)
    expect((screen.getByLabelText('Motivo de revisión') as HTMLTextAreaElement).value).toBe('Retener este motivo')
    expect(screen.getByRole('alert').textContent).toMatch(/borrador se conserva/i)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })
})
