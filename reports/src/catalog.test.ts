import { describe, expect, it } from 'vitest'
import { decodePublicReportCatalog, reportFileName, reportLabel } from './catalog'

const catalog = {
  schema_version: 'public-report-catalog-v1',
  reports: [{ key: '2026-10-11-sapa-banfield-b', date: '2026-10-11', home_team: 'S.A.P.A.', away_team: 'Banfield B' }],
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
