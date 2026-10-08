export type PlayerPublic = {
  slug: string
  name: string
  jersey_number: string | null
  team_side: 'home' | 'away'
  role: 'goalkeeper' | 'field_player'
  metrics: Record<string, string | number | null>
  evidence: Array<{ reference: string; period: number | null }>
}

export type TeamSummary = {
  name: string
  side: 'home' | 'away'
  shots: number
  goals: number
  turnovers: number
  recoveries: number
  sanctions: number
  shots_on_target: number
  saves_against: number
  outside_or_woodwork: number
}

export type Incident = {
  reference: string
  period: number | null
  regulation_seconds: number | null
  clock_unverified: boolean
  clock_label: string | null
  incident_type: string
  outcome: string
  team_side: 'home' | 'away' | 'unknown'
  player_name: string | null
  player_slug: string | null
  event_kind: string
  video_seconds: number | null
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
  team_summary: { home: TeamSummary | null; away: TeamSummary | null } | null
  incidents: Array<Incident>
  video: { provider: 'youtube'; video_id: string; availability: string } | null
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
  const rootAllowed = ['schema_version', 'report_version', 'match', 'source', 'coaching', 'metrics', 'players', 'reconciliation', 'uncertainty_disclosure', 'coverage', 'evidence', 'team_summary', 'incidents', 'video']
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
// Normalize top-level metric names: filter out internal-looking player:<db-id>:
  // and team:<db-id> keys since player details already carry public names/roles
  // in the players array; keep only public-friendly metric names.
  const normalizedMetrics: Record<string, Record<string, string | number | null>> = {}
  for (const [name, metric] of Object.entries(metrics) as [string, Record<string, string | number | null>][]) {
    // Skip metric keys that expose internal database IDs
    if (/^player:/i.test(name) || /^team:/i.test(name)) continue
    normalizedMetrics[name] = metric
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
        // Accept numeric or string jersey number, normalize to string for display
        const normalizedJersey = jersey_number !== null ? String(jersey_number) : null
        if (normalizedJersey !== null && !isString(normalizedJersey)) throw new Error('Player jersey_number must be a string or null.')
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
        validatedPlayers.push({ slug, name, jersey_number: normalizedJersey, team_side, role, metrics: metricsValidated, evidence: evidenceValidated } as PlayerPublic)
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
  // Optional team_summary (nested home/away)
  let team_summary: PublicReport['team_summary'] = null
  if ('team_summary' in value && value.team_summary !== null) {
    const ts = value.team_summary
    if (isRecord(ts)) {
      const readSummary = (raw: unknown, side: 'home' | 'away'): TeamSummary | null => {
        if (!isRecord(raw)) return null
        return {
          name: isString(raw.name) ? raw.name : '', side,
          shots: typeof raw.shots === 'number' ? raw.shots : 0,
          goals: typeof raw.goals === 'number' ? raw.goals : 0,
          turnovers: typeof raw.turnovers === 'number' ? raw.turnovers : 0,
          recoveries: typeof raw.recoveries === 'number' ? raw.recoveries : 0,
          sanctions: typeof raw.sanctions === 'number' ? raw.sanctions : 0,
          shots_on_target: typeof raw.shots_on_target === 'number' ? raw.shots_on_target : 0,
          saves_against: typeof raw.saves_against === 'number' ? raw.saves_against : 0,
          outside_or_woodwork: typeof raw.outside_or_woodwork === 'number' ? raw.outside_or_woodwork : 0,
        }
      }
      const home = readSummary(ts.home, 'home')
      const away = readSummary(ts.away, 'away')
      if (home || away) {
        team_summary = { home, away } as PublicReport['team_summary']
      }
    }
  }
  // Optional incidents (chronological, period-separated events)
  let incidents: PublicReport['incidents'] = []
  if ('incidents' in value && Array.isArray(value.incidents)) {
    incidents = value.incidents.map((item: unknown) => {
      const it = requiredRecord(item) as Record<string, unknown>
      const incident_type_map: Record<string, string> = {
        'shot': 'Lanzamiento',
        'turnover': 'Pérdida',
        'recovery': 'Recuperación',
        'foul_sanction': 'Sanción',
        'other': 'Incidencia de juego',
      }
      const outcome_map: Record<string, string> = {
        'goal': 'Gol',
        'save': 'Atajada',
        'miss': 'Fuera',
        'woodwork': 'Palo/Travesaño',
        'blocked': 'Bloqueado',
        'bad_pass': 'Pase perdido',
        'bad_reception': 'Recepción perdida',
        'foul': 'Falta',
        'yellow_card': 'Tarjeta amarilla',
        'red_card': 'Tarjeta roja',
        'two_minute_exclusion': 'Exclusión 2 min',
        'blue_card': 'Tarjeta azul',
      }
      const kind = it.event_kind as string || 'other'
      const outcome = it.outcome as string || ''
      return {
        reference: it.reference as string || 'Sequence',
        period: it.period !== undefined ? Number(it.period) : null,
        regulation_seconds: it.regulation_seconds !== undefined ? Number(it.regulation_seconds) : null,
        clock_unverified: Boolean(it.clock_unverified),
        clock_label: it.clock_label as string | null,
        incident_type: incident_type_map[kind] || 'Incidencia',
        outcome: outcome_map[outcome] || outcome || '',
        team_side: it.team_side as 'home' | 'away' | 'unknown' || 'unknown',
        player_name: it.player_name as string | null,
      player_slug: it.player_slug as string | null,
      event_kind: kind,
      video_seconds: typeof it.video_seconds === 'number' ? it.video_seconds : null,
      } as Incident
    }).filter((item): item is Incident => item.reference !== undefined)
  }
  let video: PublicReport['video'] = null
  if (isRecord(value.video)) {
    fields(value.video, ['provider', 'video_id', 'availability'], forbidden)
    if (value.video.provider === 'youtube' && isString(value.video.video_id) && /^[A-Za-z0-9_-]{6,}$/.test(value.video.video_id) && isString(value.video.availability)) {
      video = { provider: 'youtube', video_id: value.video.video_id, availability: value.video.availability }
    } else throw new Error('The public report has invalid video data.')
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
metrics: normalizedMetrics,
    players,
    reconciliation: reconciliation as PublicReport['reconciliation'],
    uncertainty_disclosure: value.uncertainty_disclosure ?? null,
    coverage,
    team_summary,
    incidents,
    video,
    evidence,
  } as PublicReport
}
