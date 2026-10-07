import { describe, expect, it, vi } from 'vitest'

const { get, post, put, patch, delete: deleteRequest, requestUse, responseUse } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  requestUse: vi.fn(),
  responseUse: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: requestUse },
        response: { use: responseUse },
      },
        get,
        post,
        put,
        patch,
        delete: deleteRequest,
    })),
  },
}))

import { approveReportPackage, attestRecoveryArtifact, confirmFixturePDF, confirmFixtureReview, createAnalysisEvent, createCanonicalEvent, createReportPackage, deactivateAnalysisEvent, enableCanonicalAnalysis, getCanonicalEvents, getCanonicalMetrics, getCanonicalPlayerProjection, getCanonicalReconciliation, getCanonicalState, getPublicationStatus, getReviewedMetrics, getWarningsSummary, previewFixturePDF, publishReportPackage, reviewFixturePDF, reviseCanonicalEvent, restoreAnalysisEvent, saveAnalysisSession } from './client'

describe('API client authentication', () => {
  it('adds the stored access token to outgoing requests', () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => 'stored-token'),
    })

    const requestInterceptor = requestUse.mock.calls[0][0]
    const config = { headers: {} }

    expect(requestInterceptor(config)).toEqual({
      headers: { Authorization: 'Bearer stored-token' },
    })
  })
})

describe('analytical event API', () => {
  it('replaces an authenticated analysis source through the match-scoped session contract', () => {
    const replacement = { mode: 'video' as const, profile: 'complete' as const, source: { url: 'https://www.youtube.com/watch?v=zyxwvutsrq', availability_state: 'ready' as const }, video_position_seconds: null, clock_start_video_seconds: null, angle: null, filters: {}, draft: {}, queue: [], anchors: [], time_segments: [] }
    put.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: replacement }) })

    saveAnalysisSession(42, replacement)

    expect(put).toHaveBeenCalledWith('/matches/42/analysis-session', replacement)
  })

  it('posts the observation to the match-scoped analytical contract', () => {
    const draft = { codebook_version: 'mvp-1' as const, code: 'turnover' as const, period: 1, regulation_seconds: 12, video_timestamp: null, clock_unverified: false, team_action: null, player_id: null, turnover_cause: 'interception', outcome: null, evidence_state: 'confirmed' as const, source: 'live', angle: null, note: null, included: true }
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: draft }) })

    createAnalysisEvent(42, draft)

    expect(post).toHaveBeenCalledWith('/matches/42/analysis-events', draft)
  })

  it('uses the canonical command and state contracts for live/video capture', () => {
    const command = { kind: 'other' as const, period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, outcome: 'kickoff', fact_kind: 'observed' as const, evidence_state: 'ambiguous' as const, uncertainty: ['responsibility_unknown'], note: null }
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: command }) })
    get.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })

    createCanonicalEvent(42, command)
    getCanonicalEvents(42)
    getCanonicalState(42)
    getCanonicalMetrics(42)
    getCanonicalReconciliation(42)
    getWarningsSummary(42)

    expect(post).toHaveBeenCalledWith('/matches/42/canonical-events', command)
    expect(get).toHaveBeenNthCalledWith(1, '/matches/42/canonical-events')
    expect(get).toHaveBeenNthCalledWith(2, '/matches/42/canonical-state')
    expect(get).toHaveBeenNthCalledWith(3, '/matches/42/canonical-metrics')
    expect(get).toHaveBeenNthCalledWith(4, '/matches/42/canonical-reconciliation')
    expect(get).toHaveBeenNthCalledWith(5, '/matches/42/warnings-summary')
  })

  it('enables the canonical cutover through the explicit preparation transition', () => {
    put.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })

    enableCanonicalAnalysis(42)

    expect(put).toHaveBeenCalledWith('/matches/42/canonical-cutover', { enabled: true, reason: 'analysis preparation started' })
  })

  it('revises canonical events through the supported per-event PATCH contract', () => {
    const revision = { kind: 'other' as const, period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, outcome: null, fact_kind: 'observed' as const, evidence_state: 'no_visible' as const, uncertainty: [], note: 'No se ve', reason: 'Revisión', evidence: [{ kind: 'unavailable' as const, uncertainty: ['not_visible'] }] }
    patch.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: revision }) })
    reviseCanonicalEvent(7, revision)
    expect(patch).toHaveBeenCalledWith('/canonical-events/7', revision)
  })

  it('serializes only supplied player projection filters', () => {
    get.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    getCanonicalPlayerProjection(42, { player_id: 9, period: 2, from_regulation_seconds: 30 })
    expect(get).toHaveBeenCalledWith('/matches/42/canonical-player-projection', { params: { player_id: 9, period: 2, from_regulation_seconds: 30 } })
  })

  it('gets read-only reviewed metrics from the match-scoped contract', () => {
    get.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })

    getReviewedMetrics(42)

    expect(get).toHaveBeenCalledWith('/matches/42/reviewed-metrics')
  })

  it('revises only a selected analytical event through audited endpoints', () => {
    deleteRequest.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })

    deactivateAnalysisEvent(7, 'review shortcut undo')
    restoreAnalysisEvent(7, 'review shortcut redo')

    expect(deleteRequest).toHaveBeenCalledWith('/analysis-events/7', { params: { reason: 'review shortcut undo' } })
    expect(post).toHaveBeenCalledWith('/analysis-events/7/restore', null, { params: { reason: 'review shortcut redo' } })
  })

  it('creates and approves reviewed packages through the authenticated API', () => {
    const packageInput = {
      coaching_question: '¿Qué sostenemos?', pattern_statement: 'Patrón visible', action_kind: 'keep' as const,
      action_text: 'Sostenerlo', uncertainty_disclosure: 'Muestra acotada', metrics: {}, reconciliation: [],
      source_label: null, source_status: null, evidence: [],
    }
    post.mockClear()
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: packageInput }) })

    createReportPackage(42, packageInput)
    approveReportPackage(7)

    expect(post).toHaveBeenNthCalledWith(1, '/matches/42/report-packages', packageInput)
    expect(post).toHaveBeenNthCalledWith(2, '/report-packages/7/approve')
  })

  it('uses the protected status, attestation, and publish contracts', () => {
    get.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    put.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })

    getPublicationStatus(7)
    attestRecoveryArtifact(7, 'postgres_dump', '/backups/match.sql')
    publishReportPackage(7)

    expect(get).toHaveBeenCalledWith('/report-packages/7/publication-status')
    expect(put).toHaveBeenCalledWith('/report-packages/7/recovery-artifacts/postgres_dump', { location: '/backups/match.sql' })
    expect(post).toHaveBeenCalledWith('/report-packages/7/publish')
  })
})

describe('fixture sheet API', () => {
  it('uses the fixture review router path under the PDF prefix', () => {
    get.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    const confirmation = { home_team_id: 1, away_team_id: 2, home_players: [], away_players: [], acknowledge_score_mismatch: false }

    reviewFixturePDF('fixture-1')
    confirmFixtureReview('fixture-1', confirmation)

    expect(get).toHaveBeenCalledWith('/pdf/fixtures/fixture-1/review')
    expect(post).toHaveBeenCalledWith('/pdf/fixtures/fixture-1/review', confirmation)
  })

  it('sends the selected fixture, PDF, and confirmation as multipart fields', () => {
    post.mockClear()
    post.mockReturnValue({ then: (resolve: (value: unknown) => unknown) => resolve({ data: {} }) })
    const file = new File(['pdf'], 'sheet.pdf', { type: 'application/pdf' })

    previewFixturePDF('fixture-1', file)
    confirmFixturePDF('fixture-1', file, { home_team_id: 1, away_team_id: 2, home_players: [], away_players: [], acknowledge_score_mismatch: true })

    const previewForm = post.mock.calls[0][1] as FormData
    const confirmForm = post.mock.calls[1][1] as FormData
    expect(post).toHaveBeenNthCalledWith(1, '/pdf/fixture-preview', expect.any(FormData))
    expect(previewForm.get('fixture_key')).toBe('fixture-1')
    expect(previewForm.get('file')).toBe(file)
    expect(post).toHaveBeenNthCalledWith(2, '/pdf/fixture-confirm', expect.any(FormData))
    expect(confirmForm.get('confirmation_json')).toContain('"acknowledge_score_mismatch":true')
  })
})
