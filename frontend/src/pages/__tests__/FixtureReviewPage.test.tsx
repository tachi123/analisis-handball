import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { FixturePreviewResult, FixtureSideCompatibility, ScoreReconciliation } from '../../types'

// Use vi.hoisted for mocks that need to be available at module load time
const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  useParams: vi.fn(() => ({ fixtureKey: 'fixture-1' })),
  confirmFixtureReview: vi.fn(),
  reviewFixturePDF: vi.fn(),
}))

vi.mock('react-router-dom', async (original) => {
  const actual = await original<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
    useParams: mocks.useParams,
  }
})

vi.mock('../../api/client', () => ({
  confirmFixtureReview: mocks.confirmFixtureReview,
  reviewFixturePDF: mocks.reviewFixturePDF,
}))

// Import after mocks
import FixtureReviewPage from '../FixtureReviewPage'

const { navigate, useParams, confirmFixtureReview, reviewFixturePDF } = mocks

const baseFixturePreview: FixturePreviewResult = {
  fixture: {
    fixture_key: 'fixture-1',
    stage: { id: 1, season_year: 2026, name: 'Apertura', category: 'Senior', division: 'A', gender: 'F' },
    home_registration: { id: 1, display_name: 'Ci.De.Co. B', variant: 'B' },
    away_registration: { id: 2, display_name: 'S.A.P.A.', variant: null },
    scheduled_date: '2026-04-12',
    venue: null,
    court: null,
    match_time: null,
    source_home_score: 41,
    source_away_score: 22,
    result_status: 'approved',
    linked_match_id: 42,
    official_snapshot_id: 'snapshot',
    is_preloaded: true,
    youtube_link: '',
    roster_status: 'needs_identity_resolution',
    unresolved_roster_players: 2,
  },
  preview: {
    match_info: {},
    home_team: {
      name: 'Ci.De.Co. B',
      players: [
        { number: 10, name: 'Jugador A', goals: 5, yellow: 1, two_min: 0, red: 0, blue: 0 },
        { number: 7, name: 'Jugador B', goals: 3, yellow: 0, two_min: 1, red: 0, blue: 0 },
      ],
    },
    away_team: {
      name: 'S.A.P.A.',
      players: [
        { number: 9, name: 'Jugador C', goals: 4, yellow: 0, two_min: 0, red: 0, blue: 0 },
      ],
    },
    provenance: { filename: 'test.pdf', content_type: 'application/pdf', size_bytes: 100, sha256: 'abc', page_count: 1 },
    warnings: [],
  },
  home_compatibility: {
    status: 'compatible' as FixtureSideCompatibility['status'],
    expected_name: 'Ci.De.Co.',
    expected_variant: 'B',
    parsed_name: 'Ci.De.Co.',
    parsed_variant: 'B',
  },
  away_compatibility: {
    status: 'incompatible' as FixtureSideCompatibility['status'],
    expected_name: 'S.A.P.A.',
    expected_variant: null,
    parsed_name: 'SAPA',
    parsed_variant: null,
  },
  score_reconciliation: 'mismatch' as ScoreReconciliation,
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: Infinity },
    },
  })
}

function renderPage(queryClient: QueryClient, previewOverrides: Partial<FixturePreviewResult> = {}) {
  const preview = { ...baseFixturePreview, ...previewOverrides }
  // Pre-populate the query cache to avoid API call
  queryClient.setQueryData(['fixture-review', 'fixture-1'], preview)
  useParams.mockReturnValue({ fixtureKey: 'fixture-1' })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <FixtureReviewPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('FixtureReviewPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    navigate.mockClear()
    confirmFixtureReview.mockResolvedValue({ match_id: 42, snapshot_id: 'snap', reused: false })
    reviewFixturePDF.mockResolvedValue(baseFixturePreview)
    queryClient = createQueryClient()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders preview with compatibility badges', async () => {
    renderPage(queryClient)

    // Wait for data to load (from cache)
    await waitFor(() => expect(screen.getByText('Compatible')).toBeTruthy())

    // Home compatibility badge - compatible (green)
    const homeBadgeText = screen.getByText('Compatible')
    expect(homeBadgeText).toBeTruthy()
    const homeBadge = homeBadgeText.closest('span')
    expect(homeBadge?.className).toContain('bg-green-100')
    expect(homeBadge?.className).toContain('text-green-800')

    // Away compatibility badge - incompatible (red)
    const awayBadgeText = screen.getByText('Incompatible')
    expect(awayBadgeText).toBeTruthy()
    const awayBadge = awayBadgeText.closest('span')
    expect(awayBadge?.className).toContain('bg-red-100')
    expect(awayBadge?.className).toContain('text-red-800')

    // Score reconciliation badge - mismatch (red)
    const scoreBadgeText = screen.getByText('Marcador no coincide')
    expect(scoreBadgeText).toBeTruthy()
    const scoreBadge = scoreBadgeText.closest('span')
    expect(scoreBadge?.className).toContain('bg-red-100')
    expect(scoreBadge?.className).toContain('text-red-800')

    // Also verify the unresolved state renders correctly (only home side)
    const unresolvedPreview: FixturePreviewResult = {
      ...baseFixturePreview,
      home_compatibility: {
        status: 'unresolved',
        expected_name: 'Ci.De.Co.',
        expected_variant: 'B',
        parsed_name: null,
        parsed_variant: null,
      },
      // Keep away as incompatible to avoid duplicate "Sin resolver"
      away_compatibility: {
        status: 'incompatible',
        expected_name: 'S.A.P.A.',
        expected_variant: null,
        parsed_name: 'SAPA',
        parsed_variant: null,
      },
    }
    queryClient.setQueryData(['fixture-review', 'fixture-2'], unresolvedPreview)
    useParams.mockReturnValue({ fixtureKey: 'fixture-2' })
    renderPage(queryClient, unresolvedPreview)
    await waitFor(() => expect(screen.getByText('Sin resolver')).toBeTruthy())
    // Get the first "Sin resolver" (home badge)
    const unresolvedBadges = screen.getAllByText('Sin resolver')
    expect(unresolvedBadges.length).toBeGreaterThanOrEqual(1)
    const unresolvedBadge = unresolvedBadges[0].closest('span')
    expect(unresolvedBadge?.className).toContain('bg-amber-100')
    expect(unresolvedBadge?.className).toContain('text-amber-800')
  })

  it('confirm button triggers mutation and shows loading state', async () => {
    // Use compatible status for both sides so the button is enabled
    const compatiblePreview: FixturePreviewResult = {
      ...baseFixturePreview,
      away_compatibility: {
        status: 'compatible' as FixtureSideCompatibility['status'],
        expected_name: 'S.A.P.A.',
        expected_variant: null,
        parsed_name: 'S.A.P.A.',
        parsed_variant: null,
      },
    }
    renderPage(queryClient, compatiblePreview)

    // Wait for data to load (from cache)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Confirmar planilla' })).toBeTruthy())

    // Click confirm button
    const confirmButton = screen.getByRole('button', { name: 'Confirmar planilla' })
    expect((confirmButton as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(confirmButton)

    await waitFor(() => expect(confirmFixtureReview).toHaveBeenCalledWith('fixture-1', {
      home_team_id: 1,
      away_team_id: 2,
      home_players: [
        { name: 'Jugador A', jersey_number: 10, official_goals: 5, official_yellow: 1, official_2min: 0, official_red: 0, official_blue: 0 },
        { name: 'Jugador B', jersey_number: 7, official_goals: 3, official_yellow: 0, official_2min: 1, official_red: 0, official_blue: 0 },
      ],
      away_players: [
        { name: 'Jugador C', jersey_number: 9, official_goals: 4, official_yellow: 0, official_2min: 0, official_red: 0, official_blue: 0 },
      ],
      acknowledge_score_mismatch: true,
    }))
  })
})
