import { describe, expect, it } from 'vitest'
import { decodePublicReportCatalog, reportFileName, reportLabel } from './catalog'

const catalog = {
  schema_version: 'public-report-catalog-v1',
  reports: [{ key: '2026-10-11-sapa-banfield-b', date: '2026-10-11', home_team: 'S.A.P.A.', away_team: 'Banfield B', summary: { home_goals: 31, away_goals: 31, home_shots: 46, away_shots: 45, home_turnovers: 9, away_turnovers: 11, coverage_status: 'complete', video_available: true, official_sheet_confirmed: true } }],
}

describe('public report catalog', () => {
  it('accepts public match metadata and derives the report filename', () => {
    const [entry] = decodePublicReportCatalog(catalog).reports
    expect(reportFileName(entry.key)).toBe('report_2026-10-11-sapa-banfield-b.json')
    expect(reportLabel(entry)).toBe('2026-10-11 · S.A.P.A. vs Banfield B')
  })

  it('rejects internal fields and unsafe report keys', () => {
    expect(() => decodePublicReportCatalog({ ...catalog, reports: [{ ...catalog.reports[0], match_id: 101 }] })).toThrow('restricted field')
    expect(() => decodePublicReportCatalog({ ...catalog, reports: [{ ...catalog.reports[0], key: '../report' }] })).toThrow('invalid key')
  })
})
