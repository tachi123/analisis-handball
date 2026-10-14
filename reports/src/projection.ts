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
  blocked: number
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

export type PhaseStats = Omit<TeamSummary, 'name' | 'side'>
export type PhaseClock = { period: number; seconds: number }
export type GoalkeeperPhaseStats = { opponent_attempts: number; opponent_on_target: number; goals_conceded: number; saves: number; seven_meters: { attempts: number; on_target: number; goals: number; saves: number } }
export type PossessionSummary = { closed_possessions: number; valid_possessions: number; average_seconds: number | null; median_seconds: number | null; ended_in_shot: number; ended_in_turnover: number; excluded_timeout: number }
export type PhaseAnalysis = {
  block_seconds: number
  blocks: Array<{ period: number; start_seconds: number; end_seconds: number; clock_overrun_seconds: number; home: PhaseStats; away: PhaseStats; winner: 'home' | 'away' | 'draw'; possessions: { home: PossessionSummary; away: PossessionSummary } }>
  scoring_runs: Array<{ team_side: 'home' | 'away'; goals: number; start: PhaseClock; end: PhaseClock }>
  quick_concessions: Array<{ conceding_side: 'home' | 'away'; scoring_side: 'home' | 'away'; seconds_after_terminal: number; terminal_kind: string; terminal_outcome: string; at: PhaseClock }>
  goalkeeper_context: { home: { total: GoalkeeperPhaseStats; first_half: GoalkeeperPhaseStats; second_half: GoalkeeperPhaseStats }; away: { total: GoalkeeperPhaseStats; first_half: GoalkeeperPhaseStats; second_half: GoalkeeperPhaseStats } }
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
  phase_analysis: PhaseAnalysis | null
  official_sheet_confirmed: boolean
  official_sheet: { label: string; href: string } | null
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

function decodeEvidence(value: unknown, allowedNames: string[]) {
  const item = requiredRecord(value)
  fields(item, allowedNames, forbidden)
  if (!isString(item.reference)) throw new Error('Evidence reference must be a string.')
  if (item.period !== undefined && item.period !== null && typeof item.period !== 'number') throw new Error('Evidence period must be a number or null.')
  if (item.regulation_seconds !== undefined && item.regulation_seconds !== null && typeof item.regulation_seconds !== 'number') throw new Error('Evidence regulation_seconds must be a number or null.')
  if (item.clock_unverified !== undefined && typeof item.clock_unverified !== 'boolean') throw new Error('Evidence clock_unverified must be a boolean.')
  if (item.observation !== undefined && item.observation !== null && !isString(item.observation)) throw new Error('Evidence observation must be a string or null.')
  if (item.media_available !== undefined && typeof item.media_available !== 'boolean') throw new Error('Evidence media_available must be a boolean.')
  if (item.media_url !== undefined && !isString(item.media_url)) throw new Error('Evidence media_url must be a string.')
  return {
    reference: item.reference,
    period: item.period ?? null,
    ...(allowedNames.includes('regulation_seconds') ? { regulation_seconds: item.regulation_seconds ?? null } : {}),
    ...(allowedNames.includes('clock_unverified') ? { clock_unverified: item.clock_unverified ?? false } : {}),
    ...(allowedNames.includes('observation') ? { observation: item.observation ?? null } : {}),
    ...(allowedNames.includes('media_available') ? { media_available: item.media_available ?? false } : {}),
    ...(item.media_url !== undefined ? { media_url: item.media_url } : {}),
  }
}

export function decodePublicReport(value: unknown): PublicReport {
  if (!isRecord(value)) throw new Error('The public report is not a JSON object.')
  // Validate root allowlist
  const rootAllowed = ['schema_version', 'report_version', 'match', 'source', 'coaching', 'metrics', 'players', 'reconciliation', 'uncertainty_disclosure', 'coverage', 'evidence', 'team_summary', 'incidents', 'video', 'phase_analysis', 'official_sheet_confirmed', 'official_sheet']
  fields(value as Record<string, unknown>, rootAllowed, forbidden)
  if (value.schema_version !== 'public-report-v1' || typeof value.report_version !== 'number') throw new Error('Unsupported public report version.')
  if (value.official_sheet_confirmed !== undefined && typeof value.official_sheet_confirmed !== 'boolean') throw new Error('The public report has invalid official sheet data.')
  let official_sheet: PublicReport['official_sheet'] = null
  if (value.official_sheet !== null && value.official_sheet !== undefined) {
    const sheet = requiredRecord(value.official_sheet)
    fields(sheet, ['label', 'href'], forbidden)
    if (sheet.label !== 'Planilla oficial FEMEBAL' || !isString(sheet.href) || !/^planillas\/planilla_[a-z0-9]+(?:-[a-z0-9]+)*\.pdf$/.test(sheet.href)) throw new Error('The public report has invalid official sheet data.')
    official_sheet = { label: sheet.label, href: sheet.href }
  }
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
        fields(item, ['slug', 'name', 'jersey_number', 'team_side', 'role', 'metrics', 'evidence'], forbidden)
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
          return decodeEvidence(ev, ['reference', 'period']) as PlayerPublic['evidence'][number]
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
    return decodeEvidence(item, ['reference', 'period', 'regulation_seconds', 'clock_unverified', 'observation', 'media_available', 'media_url']) as PublicReport['evidence'][number]
  })
  if (evidence.some((item) => item.media_url && !item.media_available)) throw new Error('The public report contains unavailable media.')
  // Reconciliation
  const reconciliation = value.reconciliation.map((item: unknown) => {
    const entry = requiredRecord(item)
    fields(entry, ['side', 'official', 'analytical', 'discrepancy'], forbidden)
    for (const key of ['side', 'official', 'analytical', 'discrepancy']) {
      const field = entry[key]
      if (field !== undefined && field !== null && typeof field !== 'string' && typeof field !== 'number') throw new Error('The public report has invalid reconciliation data.')
    }
    return { side: entry.side ?? null, official: entry.official ?? null, analytical: entry.analytical ?? null, ...(entry.discrepancy !== undefined ? { discrepancy: entry.discrepancy as string | number | null } : {}) }
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
          blocked: typeof raw.blocked === 'number' ? raw.blocked : 0,
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
      fields(it, ['reference', 'period', 'regulation_seconds', 'clock_unverified', 'clock_label', 'incident_type', 'outcome', 'team_side', 'player_name', 'player_slug', 'event_kind', 'video_seconds'], forbidden)
      if (!isString(it.reference) || (it.period !== null && it.period !== undefined && typeof it.period !== 'number') || (it.regulation_seconds !== null && it.regulation_seconds !== undefined && typeof it.regulation_seconds !== 'number') || (it.clock_unverified !== undefined && typeof it.clock_unverified !== 'boolean') || (it.clock_label !== null && it.clock_label !== undefined && !isString(it.clock_label)) || (it.team_side !== undefined && it.team_side !== 'home' && it.team_side !== 'away' && it.team_side !== 'unknown') || (it.player_name !== null && it.player_name !== undefined && !isString(it.player_name)) || (it.player_slug !== null && it.player_slug !== undefined && !isSlug(it.player_slug)) || !isString(it.event_kind) || (it.video_seconds !== null && it.video_seconds !== undefined && typeof it.video_seconds !== 'number')) throw new Error('The public report has invalid incident data.')
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
  let phase_analysis: PublicReport['phase_analysis'] = null
  if (isRecord(value.phase_analysis)) {
    const raw = value.phase_analysis
    fields(raw, ['block_seconds', 'blocks', 'scoring_runs', 'quick_concessions', 'goalkeeper_context'], forbidden)
    if (raw.block_seconds !== 600 || !Array.isArray(raw.blocks) || !Array.isArray(raw.scoring_runs) || !Array.isArray(raw.quick_concessions) || !isRecord(raw.goalkeeper_context)) throw new Error('The public report has invalid phase analysis.')
    const stats = (item: unknown): PhaseStats => {
      const entry = requiredRecord(item)
      fields(entry, ['shots', 'goals', 'turnovers', 'recoveries', 'sanctions', 'shots_on_target', 'saves_against', 'outside_or_woodwork', 'blocked'], forbidden)
      const result = {} as PhaseStats
      for (const key of ['shots', 'goals', 'turnovers', 'recoveries', 'sanctions', 'shots_on_target', 'saves_against', 'outside_or_woodwork', 'blocked'] as const) {
        if (typeof entry[key] !== 'number') throw new Error('The public report has invalid phase metrics.')
        result[key] = entry[key] as never
      }
      return result
    }
    const blocks = raw.blocks.map((item) => {
      const entry = requiredRecord(item)
      fields(entry, ['period', 'start_seconds', 'end_seconds', 'clock_overrun_seconds', 'home', 'away', 'winner', 'possessions'], forbidden)
      if (![1, 2].includes(entry.period as number) || typeof entry.start_seconds !== 'number' || typeof entry.end_seconds !== 'number' || typeof entry.clock_overrun_seconds !== 'number' || !['home', 'away', 'draw'].includes(entry.winner as string)) throw new Error('The public report has invalid phase block.')
      const possession = (raw: unknown): PossessionSummary => {
        const value = requiredRecord(raw); fields(value, ['closed_possessions', 'valid_possessions', 'average_seconds', 'median_seconds', 'ended_in_shot', 'ended_in_turnover', 'excluded_timeout'], forbidden)
        for (const key of ['closed_possessions', 'valid_possessions', 'ended_in_shot', 'ended_in_turnover', 'excluded_timeout']) if (typeof value[key] !== 'number') throw new Error('The public report has invalid possession summary.')
        if (value.average_seconds !== null && typeof value.average_seconds !== 'number' || value.median_seconds !== null && typeof value.median_seconds !== 'number') throw new Error('The public report has invalid possession duration.')
        return { closed_possessions: value.closed_possessions as number, valid_possessions: value.valid_possessions as number, average_seconds: value.average_seconds as number | null, median_seconds: value.median_seconds as number | null, ended_in_shot: value.ended_in_shot as number, ended_in_turnover: value.ended_in_turnover as number, excluded_timeout: value.excluded_timeout as number }
      }
      const possessions = requiredRecord(entry.possessions); fields(possessions, ['home', 'away'], forbidden)
      return { period: entry.period as number, start_seconds: entry.start_seconds as number, end_seconds: entry.end_seconds as number, clock_overrun_seconds: entry.clock_overrun_seconds as number, home: stats(entry.home), away: stats(entry.away), winner: entry.winner as 'home' | 'away' | 'draw', possessions: { home: possession(possessions.home), away: possession(possessions.away) } }
    })
    const clock = (item: unknown): PhaseClock => {
      const entry = requiredRecord(item); fields(entry, ['period', 'seconds'], forbidden)
      if (![1, 2].includes(entry.period as number) || typeof entry.seconds !== 'number') throw new Error('The public report has invalid phase clock.')
      return { period: entry.period as number, seconds: entry.seconds as number }
    }
    const scoring_runs = raw.scoring_runs.map((item) => {
      const entry = requiredRecord(item); fields(entry, ['team_side', 'goals', 'start', 'end'], forbidden)
      if (!['home', 'away'].includes(entry.team_side as string) || typeof entry.goals !== 'number') throw new Error('The public report has invalid scoring run.')
      return { team_side: entry.team_side as 'home' | 'away', goals: entry.goals as number, start: clock(entry.start), end: clock(entry.end) }
    })
    const quick_concessions = raw.quick_concessions.map((item) => {
      const entry = requiredRecord(item); fields(entry, ['conceding_side', 'scoring_side', 'seconds_after_terminal', 'terminal_kind', 'terminal_outcome', 'at'], forbidden)
      if (!['home', 'away'].includes(entry.conceding_side as string) || !['home', 'away'].includes(entry.scoring_side as string) || typeof entry.seconds_after_terminal !== 'number' || !isString(entry.terminal_kind) || !isString(entry.terminal_outcome)) throw new Error('The public report has invalid quick concession.')
      return { conceding_side: entry.conceding_side as 'home' | 'away', scoring_side: entry.scoring_side as 'home' | 'away', seconds_after_terminal: entry.seconds_after_terminal as number, terminal_kind: entry.terminal_kind as string, terminal_outcome: entry.terminal_outcome as string, at: clock(entry.at) }
    })
    const keeperContext = (item: unknown): GoalkeeperPhaseStats => {
      const entry = requiredRecord(item); fields(entry, ['opponent_attempts', 'opponent_on_target', 'goals_conceded', 'saves', 'seven_meters'], forbidden)
      for (const key of ['opponent_attempts', 'opponent_on_target', 'goals_conceded', 'saves']) if (typeof entry[key] !== 'number') throw new Error('The public report has invalid goalkeeper context.')
      const seven = requiredRecord(entry.seven_meters); fields(seven, ['attempts', 'on_target', 'goals', 'saves'], forbidden)
      for (const key of ['attempts', 'on_target', 'goals', 'saves']) if (typeof seven[key] !== 'number') throw new Error('The public report has invalid seven-metre context.')
      return { opponent_attempts: entry.opponent_attempts as number, opponent_on_target: entry.opponent_on_target as number, goals_conceded: entry.goals_conceded as number, saves: entry.saves as number, seven_meters: { attempts: seven.attempts as number, on_target: seven.on_target as number, goals: seven.goals as number, saves: seven.saves as number } }
    }
    const teamKeeperContext = (item: unknown) => { const entry = requiredRecord(item); fields(entry, ['total', 'first_half', 'second_half'], forbidden); return { total: keeperContext(entry.total), first_half: keeperContext(entry.first_half), second_half: keeperContext(entry.second_half) } }
    phase_analysis = { block_seconds: 600, blocks, scoring_runs, quick_concessions, goalkeeper_context: { home: teamKeeperContext(raw.goalkeeper_context.home), away: teamKeeperContext(raw.goalkeeper_context.away) } }
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
    phase_analysis,
    official_sheet_confirmed: value.official_sheet_confirmed === true,
    official_sheet,
  } as PublicReport
}
