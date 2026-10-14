// The allowlists below are the privacy boundary. Keep this narrow so harmless
// public words such as "video" are not rejected merely because they contain "id".
const forbidden = /^(?:private|raw|analysis|event|database|credential|api|token|url|id)$/i
const keyPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export type PublicReportCatalogEntry = {
  key: string
  date: string | null
  home_team: string
  away_team: string
  summary: {
    home_goals: number
    away_goals: number
    home_shots: number
    away_shots: number
    home_turnovers: number
    away_turnovers: number
    coverage_status: 'complete' | 'partial' | null
    video_available: boolean
    official_sheet_confirmed: boolean
  }
}

export type PublicReportCatalog = {
  schema_version: 'public-report-catalog-v1'
  reports: PublicReportCatalogEntry[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function reportFileName(key: string) {
  return `report_${key}.json`
}

export function reportLabel(report: PublicReportCatalogEntry) {
  return `${report.date ?? 'Fecha sin confirmar'} · ${report.home_team} vs ${report.away_team}`
}

export function decodePublicReportCatalog(value: unknown): PublicReportCatalog {
  if (!isRecord(value) || value.schema_version !== 'public-report-catalog-v1' || !Array.isArray(value.reports)) {
    throw new Error('The public report catalog has invalid data.')
  }

  return {
    schema_version: 'public-report-catalog-v1',
    reports: value.reports.map((item) => {
      if (!isRecord(item) || Object.keys(item).some((field) => !['key', 'date', 'home_team', 'away_team', 'summary'].includes(field) || forbidden.test(field))) {
        throw new Error('The public report catalog contains a restricted field.')
      }
      if (typeof item.key !== 'string' || !keyPattern.test(item.key)) throw new Error('The public report catalog has an invalid key.')
      if (item.date !== null && typeof item.date !== 'string') throw new Error('The public report catalog has an invalid date.')
      if (typeof item.home_team !== 'string' || typeof item.away_team !== 'string') throw new Error('The public report catalog has invalid teams.')
      if (!isRecord(item.summary) || Object.keys(item.summary).some((field) => !['home_goals', 'away_goals', 'home_shots', 'away_shots', 'home_turnovers', 'away_turnovers', 'coverage_status', 'video_available', 'official_sheet_confirmed'].includes(field) || forbidden.test(field))) throw new Error('The public report catalog has an invalid summary.')
      const summary = item.summary
      for (const field of ['home_goals', 'away_goals', 'home_shots', 'away_shots', 'home_turnovers', 'away_turnovers']) if (typeof summary[field] !== 'number' || summary[field] < 0) throw new Error('The public report catalog has an invalid summary.')
      if (summary.coverage_status !== null && summary.coverage_status !== 'complete' && summary.coverage_status !== 'partial') throw new Error('The public report catalog has an invalid summary.')
      if (typeof summary.video_available !== 'boolean' || typeof summary.official_sheet_confirmed !== 'boolean') throw new Error('The public report catalog has an invalid summary.')
      return { key: item.key, date: item.date, home_team: item.home_team, away_team: item.away_team, summary: summary as PublicReportCatalogEntry['summary'] }
    }),
  }
}
