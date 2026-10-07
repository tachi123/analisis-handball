import { describe, expect, it } from 'vitest'
import { parseVideoPosition } from './MatchReviewVideoSection'

describe('parseVideoPosition', () => {
  it('accepts seconds and mm:ss without accepting a game-clock value', () => {
    expect(parseVideoPosition('83')).toBe(83)
    expect(parseVideoPosition('01:23')).toBe(83)
  })

  it('rejects negative and invalid video positions', () => {
    expect(parseVideoPosition('-1')).toBeNull()
    expect(parseVideoPosition('01:60')).toBeNull()
    expect(parseVideoPosition('')).toBeNull()
  })
})
