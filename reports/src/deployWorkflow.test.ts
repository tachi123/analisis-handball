import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const workflow = readFileSync(new URL('../../.github/workflows/deploy-frontend.yml', import.meta.url), 'utf8')

describe('Pages deployment workflow', () => {
  it('deploys ONLY reports/dist as the Pages artifact', () => {
    // Reports-only deployment: no frontend paths, no combined site/
    expect(workflow).not.toContain("- 'frontend/**'")
    expect(workflow).not.toContain('cp -R frontend')
    expect(workflow).toContain("- 'reports/**'")
  })

  it('workflow builds reports only', () => {
    expect(workflow).toContain('npm --prefix reports run build')
    // Should not build frontend
    expect(workflow).not.toContain('npm --prefix frontend run build')
  })

  it('workflow does not select frontend/ or reports/ as branch folder for Pages', () => {
    // The workflow uploads reports/dist, not a branch folder selection
    expect(workflow).not.toContain('source: frontend/')
    expect(workflow).not.toContain('source: reports/')
  })
})
