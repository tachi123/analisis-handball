export type PlayerPublic = {
  slug: string
  name: string
  jersey_number: string | null
  team_side: 'home' | 'away'
  role: 'goalkeeper' | 'field_player'
  metrics: Record<string, string | number | null>
  evidence: Array<{ reference: string; period: number | null }>
}

export type PublicReport = {
  schema_version: 'public-report-v1'
  report_version: number
  match: { date: string | null; home_team: string | null; away_team: string | null }
  source: { label: string | null; status: string | null }
  coaching: { question: string | null; pattern_statement: string | null; action: { kind: string | null; text: string | null } }
  metrics: Record<string, Record<string, string | number | null>>
  players: Array<PlayerPublic> | null
  reconciliation: Array<{ side: string | null; official: string | number | null; analytical: string | number | null; discrepancy?: string | number | null }>
  uncertainty_disclosure: string | null
  coverage: { analyzed_periods: number[] | null; status: 'partial' | 'complete' | null; label: string | null } | null
  evidence: Array<{ reference: string; period: number | null; regulation_seconds: number | null; clock_unverified: boolean; observation: string | null; media_available: boolean; media_url?: string }>
}

const forbidden = /^(private_note|raw_events?|analysis_event_id|credentials?|api_?key|token|database|local_database|operational_api_url)$/i

const isString = (value: unknown): value is string => typeof value === 'string'
const isSlug = (value: unknown): value is string => isString(value) && /^[a-z0-9-]+$/.test(value)

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function validateCoverageStatus(status: unknown): asserts status is 'partial' | 'complete' {
  if (status === null || status === undefined) return
  if (typeof status !== 'string') throw new Error('Coverage status must be a string: "partial" or "complete".')
  if (status !== 'partial' && status !== 'complete') throw new Error('Coverage status must be "partial" or "complete".')
}

function fields(value: Record<string, unknown>, allowedNames: string[], forbiddenPattern: RegExp) {
  for (const key of Object.keys(value)) {
    if (!allowedNames.includes(key)) throw new Error('The public report contains a restricted field.')
    if (forbiddenPattern.test(key)) throw new Error('The public report contains a restricted field.')
  }
  return value
}

function requiredRecord(value: unknown) { if (!isRecord(value)) throw new Error('The public report has invalid data.'); return value }
function requiredArray(value: unknown) { if (!Array.isArray(value)) throw new Error('The public report has invalid data.'); return value }

export function decodePublicReport(value: unknown): PublicReport {
  if (!isRecord(value)) throw new Error('The public report is not a JSON object.')
  // Validate root allowlist
  const rootAllowed = ['schema_version', 'report_version', 'match', 'source', 'coaching', 'metrics', 'players', 'reconciliation', 'uncertainty_disclosure', 'coverage', 'evidence']
  fields(value as Record<string, unknown>, rootAllowed, forbidden)
  if (value.schema_version !== 'public-report-v1' || typeof value.report_version !== 'number') throw new Error('Unsupported public report version.')
  const match = requiredRecord(value.match)
  const source = requiredRecord(value.source)
  const coaching = requiredRecord(value.coaching)
  const action = requiredRecord(coaching.action)
  // Derive metrics
  if (!isRecord(value.metrics) || !Array.isArray(value.reconciliation)) throw new Error('The public report has invalid data.')
  const metrics: Record<string, Record<string, string | number | null>> = {}
  for (const [name, metric] of Object.entries(value.metrics) as [string, Record<string, string | number | null>][]) {
    const m: Record<string, string | number | null> = {}
    for (const [field, val] of Object.entries(metric) as [string, string | number | null][]) {
      if (field === 'count') m.count = val as number
      else if (field === 'numerator') m.numerator = val as number
      else if (field === 'denominator') m.denominator = typeof val === 'number' ? val : null
      else if (field === 'excluded') m.excluded = val as number
      else if (field === 'unknown') m.unknown = val as number
      else if (field === 'clock_unverified') m.clock_unverified = val as number
      else throw new Error('The public report contains a restricted field.')
    }
    metrics[name] = m
  }
// Optional players: explicit array of public player summaries; role must be explicitly provided
  let players: PublicReport['players'] = null
  if ('players' in value && value.players !== null) {
    const playersInput = value.players
    if (Array.isArray(playersInput)) {
      const validatedPlayers: PlayerPublic[] = []
      for (const item of playersInput) {
        if (!isRecord(item)) throw new Error('Each player entry must be a JSON object.')
        // Validate player-level fields: slug, name, jersey_number, team_side, role, metrics, evidence
        const { slug, name, jersey_number, team_side, role, metrics: metricsRaw, evidence: evidenceRaw } = item
        if (!isSlug(slug)) throw new Error('Player slug must be a safe public slug (lowercase alphanumeric and hyphens).')
        if (!isString(name)) throw new Error('Player name must be a string.')
        if (jersey_number !== null && !isString(jersey_number)) throw new Error('Player jersey_number must be a string or null.')
        if (team_side !== 'home' && team_side !== 'away') throw new Error('Player team_side must be "home" or "away".')
        // Validate role is explicitly provided and is a valid value
        if (!role) throw new Error('Player role is required and must be "goalkeeper" or "field_player".')
        if (role !== 'goalkeeper' && role !== 'field_player') throw new Error('Player role must be "goalkeeper" or "field_player".')
        // Validate metrics sub-fields (accept approved aggregate metric names as keys)
        const metricsValidated: Record<string, string | number | null> = {}
        for (const [field, val] of Object.entries(metricsRaw || {})) {
          if (!forbidden.test(field)) {
            // Normalize denominator: accept number or convert 'not_applicable' string to null
            if (field === 'denominator') {
              metricsValidated[field] = typeof val === 'number' ? val : null
            } else {
              metricsValidated[field] = val as string | number | null
            }
          } else throw new Error('The public report contains a restricted field.')
        }
        // Validate evidence sub-entries
        const evidenceValidated = ((evidenceRaw || []) as Array<unknown>).map((ev: unknown) => {
          if (!isRecord(ev)) throw new Error('Each evidence entry must be a JSON object.')
          const e: Record<string, unknown> = ev as Record<string, unknown>
          // Allowed evidence fields: reference, period, regulation_seconds, clock_unverified, observation, media_available, media_url
          if ('reference' in e) e.reference = String(e.reference)
          if ('period' in e) e.period = e.period !== undefined ? Number(e.period) : undefined
          if ('regulation_seconds' in e) e.regulation_seconds = e.regulation_seconds !== undefined ? Number(e.regulation_seconds) : undefined
          if ('clock_unverified' in e) e.clock_unverified = Boolean(e.clock_unverified)
          if ('observation' in e) e.observation = String(e.observation)
          if ('media_available' in e) e.media_available = Boolean(e.media_available)
          if ('media_url' in e) e.media_url = String(e.media_url)
          return e as PublicReport['evidence'][number]
        })
        validatedPlayers.push({ slug, name, jersey_number: jersey_number ?? null, team_side, role, metrics: metricsValidated, evidence: evidenceValidated } as PlayerPublic)
      }
      // If we validated players, set the result
      if (validatedPlayers.length > 0) {
        players = validatedPlayers as PublicReport['players']
      }
    }
  }
  // Evidence
  const evidence = requiredArray(value.evidence).map((item: unknown) => {
    const e = requiredRecord(item) as Record<string, unknown>
    // Allowed evidence fields: reference, period, regulation_seconds, clock_unverified, observation, media_available, media_url
    if ('reference' in e) e.reference = String(e.reference)
    if ('period' in e) e.period = e.period !== undefined ? Number(e.period) : undefined
    if ('regulation_seconds' in e) e.regulation_seconds = e.regulation_seconds !== undefined ? Number(e.regulation_seconds) : undefined
    if ('clock_unverified' in e) e.clock_unverified = Boolean(e.clock_unverified)
    if ('observation' in e) e.observation = String(e.observation)
    if ('media_available' in e) e.media_available = Boolean(e.media_available)
    if ('media_url' in e) e.media_url = String(e.media_url)
    return e as PublicReport['evidence'][number]
  })
  if (evidence.some((item) => item.media_url && !item.media_available)) throw new Error('The public report contains unavailable media.')
  // Reconciliation
  const reconciliation = value.reconciliation.map((item: unknown) => requiredRecord(item) as {
    side: string | null; official: string | number | null; analytical: string | number | null; discrepancy?: string | number | null
  })
  // Optional coverage
  let coverage: PublicReport['coverage'] = null
  if ('coverage' in value) {
    const cov = value.coverage
    if (isRecord(cov)) {
      validateCoverageStatus((cov as Record<string, unknown>).status)
      coverage = {
        analyzed_periods: (cov as Record<string, unknown>).analyzed_periods as number[] | null,
        status: (cov as Record<string, unknown>).status as 'partial' | 'complete' | null,
        label: (cov as Record<string, unknown>).label as string | null,
      }
    }
  }
  return {
    schema_version: value.schema_version,
    report_version: value.report_version,
    match: {
      date: match.date ?? null,
      home_team: match.home_team ?? null,
      away_team: match.away_team ?? null,
    } as PublicReport['match'],
    source: {
      label: source.label ?? null,
      status: source.status ?? null,
    } as PublicReport['source'],
    coaching: {
      question: coaching.question ?? null,
      pattern_statement: coaching.pattern_statement ?? null,
      action: {
        kind: action.kind ?? null,
        text: action.text ?? null,
      } as PublicReport['coaching']['action'],
    },
    metrics,
    players,
    reconciliation: reconciliation as PublicReport['reconciliation'],
    uncertainty_disclosure: value.uncertainty_disclosure ?? null,
    coverage,
    evidence,
  } as PublicReport
}