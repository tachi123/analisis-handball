import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import GkCourtPicker from './GkCourtPicker'

describe('GkCourtPicker', () => {
  it('exposes only numeric IHF 1–9 target zones and never legacy origins', () => {
    const onChange = vi.fn()
    render(<GkCourtPicker value={null} onChange={onChange} />)

    expect(screen.getAllByRole('button')).toHaveLength(9)
    expect(screen.queryByText(/6m_|9m_|wing_|seven_meter|counter/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Zona IHF 9' }))
    expect(onChange).toHaveBeenCalledWith(9)
  })
})
