const forbidden = /(?:private|raw|analysis|event|database|credential|api|token|url|id)/i
const keyPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

export type PublicReportCatalogEntry = {
  key: string
  date: string | null
  home_team: string
  away_team: string
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
      if (!isRecord(item) || Object.keys(item).some((field) => !['key', 'date', 'home_team', 'away_team'].includes(field) || forbidden.test(field))) {
        throw new Error('The public report catalog contains a restricted field.')
      }
      if (typeof item.key !== 'string' || !keyPattern.test(item.key)) throw new Error('The public report catalog has an invalid key.')
      if (item.date !== null && typeof item.date !== 'string') throw new Error('The public report catalog has an invalid date.')
      if (typeof item.home_team !== 'string' || typeof item.away_team !== 'string') throw new Error('The public report catalog has invalid teams.')
      return { key: item.key, date: item.date, home_team: item.home_team, away_team: item.away_team }
    }),
  }
}
