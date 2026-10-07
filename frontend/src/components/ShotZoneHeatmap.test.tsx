import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ShotZoneHeatmap from './ShotZoneHeatmap'

describe('ShotZoneHeatmap', () => {
  it('renders server buckets and explicit unknown coverage', () => {
    render(<ShotZoneHeatmap zones={{ '1': 2 }} coverage={{ recorded: 2, missing_zone: 1, goalkeeper_unknown: 3, excluded: 0, unknown: 0, clock_unverified: 4 }} />)
    expect(screen.getByLabelText('Zona IHF 1: 2 tiros')).not.toBeNull()
    expect(screen.getByText('Arquero desconocido')).not.toBeNull()
    expect(screen.getByText('Reloj sin verificar')).not.toBeNull()
  })
})
