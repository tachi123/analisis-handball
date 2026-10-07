import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import MatchAnalysis from './MatchAnalysis'

describe('MatchAnalysis legacy route', () => {
  it('redirects to the persisted video review workspace instead of creating a second timer', () => {
    render(<MemoryRouter initialEntries={['/match/16/analysis']}><Routes><Route path="/match/:matchId/analysis" element={<MatchAnalysis />} /><Route path="/match/:matchId/review" element={<p>Persisted review</p>} /></Routes></MemoryRouter>)
    expect(screen.getByText('Persisted review')).toBeTruthy()
  })
})
