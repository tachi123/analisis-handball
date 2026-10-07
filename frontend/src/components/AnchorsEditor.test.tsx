import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import AnchorsEditor from './AnchorsEditor'

describe('AnchorsEditor runtime scenario', () => {
  it('sets a new anchor from the player position while requiring explicit regulation time', () => {
    const onSave = vi.fn()
    render(<AnchorsEditor anchors={[]} currentVideoTime={83.5} onSave={onSave} />)

    fireEvent.click(screen.getByRole('button', { name: /agregar anclaje/i }))
    expect((screen.getByLabelText('Tiempo de video 1') as HTMLInputElement).value).toBe('83.5')
    fireEvent.change(screen.getByLabelText('Tiempo reglamentario 1'), { target: { value: '42' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar anclajes/i }))
    expect(onSave).toHaveBeenCalledWith([expect.objectContaining({ video_seconds: 83.5, regulation_seconds: 42 })])
  })

  it('gives anchor input and destructive controls a 44px review target', () => {
    render(<AnchorsEditor anchors={[{ id: 1, period: 1, video_seconds: 5, regulation_seconds: 0, uncertainty_seconds: 0 }]} currentVideoTime={83.5} onSave={vi.fn()} />)

    expect(screen.getByLabelText('Tiempo de video 1').className).toContain('review-target')
    expect(screen.getByRole('button', { name: /eliminar/i }).className).toContain('review-target')
  })
})
