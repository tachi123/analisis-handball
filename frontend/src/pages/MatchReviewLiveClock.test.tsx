import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LiveClock } from './MatchReviewLiveClock'

describe('LiveClock', () => {
  it('exposes explicit start, pause, and reset controls', () => {
    const onStart = vi.fn(); const onPause = vi.fn(); const onReset = vi.fn()
    render(<LiveClock seconds={65} running={false} onStart={onStart} onPause={onPause} onReset={onReset} />)

    expect(screen.getByText('01:05')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reiniciar' }))
    expect(onStart).toHaveBeenCalledOnce()
    expect(onReset).toHaveBeenCalledOnce()
    expect((screen.getByRole('button', { name: 'Pausar' }) as HTMLButtonElement).disabled).toBe(true)
  })
})
